from .state import ConversationState
from .tools import tools
from .llm import llm, classifier_llm
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain.tools.render import format_tool_to_openai_function
import json
import re
from datetime import datetime
from app.crud.crud_coupon import get_coupon_by_code, get_all_coupons
from app.services.coupon_service import CouponService
from sqlalchemy.orm import Session
from .history import save_history, load_history

# Helper to convert tools for LLM function calling
functions = [format_tool_to_openai_function(t) for t in tools]
llm_with_tools = llm.bind_functions(functions)
classifier_llm_with_tools = classifier_llm.bind_functions(functions)

def detect_frustration(user_message: str) -> bool:
    frustration_keywords = [
        "angry", "frustrated", "useless", "not working", "annoyed", "mad", "upset", "hate", "stupid", "idiot", "terrible", "worst", "bad service"
    ]
    return any(word in user_message.lower() for word in frustration_keywords)

def frustration_node(state: ConversationState):
    print("--- Node: Frustration ---")
    state['bot_message'] = "It seems you're having trouble. Would you like to be routed to a real person named Ahmad?"
    return state

def manager_approval_node(state: ConversationState):
    print("--- Node: Manager Approval ---")
    state['bot_message'] = (
        "This request requires manager approval. Please wait while I notify a manager. "
        "You will be notified once Ahmad (the manager) has approved your request."
    )
    state['manager_approval_required'] = True
    return state

# Define frustration detection functions
# We'll use these in the classify_intent_node function

def classify_intent_node(state: ConversationState):
    """Classifies the user's intent based on the latest message."""
    print("--- Node: Classify Intent ---")
    user_message = state['user_message']
    messages = state['messages']
    
    # Detect refund request
    if 'refund' in user_message.lower():
        print("--- Detected refund request, routing to manager approval ---")
        return {"intent": "manager_approval"}
    
    # Detect frustration
    is_frustrated = detect_frustration(user_message)
    frustration_count = state.get('frustration_count', 0)
    if is_frustrated:
        frustration_count += 1
        print(f"--- Frustration detected! Count: {frustration_count} ---")
    state['frustration_count'] = frustration_count
    
    # Also include frustration_count in the return value
    # This ensures it's properly passed to the next node
    
    # Check for coupon-related queries with a simple regex pattern
    coupon_patterns = [
        r'coupon', r'discount', r'promo code', r'promotion', r'offer', r'deal'
    ]
    
    # Check if any coupon-related pattern is in the message
    if any(re.search(pattern, user_message.lower()) for pattern in coupon_patterns):
        print("--- Detected coupon-related query ---")
        return {"intent": "coupon_query"}
        
    # Check for product-related queries with simple regex patterns
    product_patterns = [
        r'product', r'item', r'merchandise', r'goods', r'stock', r'inventory',
        r'do you (have|sell|offer)', r'what (products|items)', r'looking for',
        r'shirt', r'clothing', r'electronics', r'available'
    ]
    
    # Check if any product-related pattern is in the message
    if any(re.search(pattern, user_message.lower()) for pattern in product_patterns):
        print("--- Detected product-related query ---")
        return {"intent": "product_availability"}
    
    # Check if the message is just a number (likely an order number)
    if re.match(r'^\d+$', user_message.strip()):
        print(f"--- Detected numeric input '{user_message}', treating as order number ---")
        # For simple numeric inputs, directly set the order number in the state
        order_number = user_message.strip()
        return {"intent": "order_status", "extracted_order_number": order_number}
        
    # Simple prompt for classification
    prompt = f"""Based on the following user message and conversation history, classify the primary intent. Choose ONE from: 'order_status', 'knowledge_base_query', 'product_availability', 'greeting', 'other'.

    Conversation History:
    {[f'{m.type}: {m.content}' for m in messages]}

    User Message: {user_message}

    Intent:"""

    response = classifier_llm.invoke(prompt)
    intent = response.content.strip().lower()

    # Basic validation/cleanup
    allowed_intents = ['order_status', 'knowledge_base_query', 'product_availability', 'greeting', 'other']
    if intent not in allowed_intents:
        print(f"--- Classified intent '{intent}' not in allowed list, defaulting to 'knowledge_base_query'. ---")
        intent = 'knowledge_base_query'

    print(f"--- Classified Intent: {intent} ---")
    
    # If the result is an error or fallback, increment frustration_count
    if intent == 'other':
        frustration_count += 1
        state['frustration_count'] = frustration_count
        print(f"--- Incremented frustration for 'other' intent. New count: {frustration_count} ---")
    
    return {"intent": intent, "frustration_count": frustration_count}

def order_status_node(state: ConversationState):
    """Handles order status queries and provides status information for orders 1-5."""
    print("--- Node: Order Status ---")
    user_message = state['user_message']
    messages = state['messages']
    language = state.get('language', 'en')  # Get language from state
    
    # Check if order number was already extracted in the classify_intent_node
    extracted_order_number = state.get('extracted_order_number')
    if extracted_order_number:
        print(f"--- Using pre-extracted order number: {extracted_order_number} ---")
        return process_order_status(extracted_order_number, language)
    
    # Use LLM to extract order number from user message
    # This is more flexible than regex and can handle a wider variety of user inputs
    conversation_context = "\n".join([f"{m.type}: {m.content}" for m in messages[-3:] if hasattr(m, 'type') and hasattr(m, 'content')])
    
    # Check for simple numeric input first (most common case after being asked for order number)
    if re.match(r'^\d+$', user_message.strip()):
        order_number = user_message.strip()
        print(f"--- Detected simple numeric input: {order_number} ---")
        return process_order_status(order_number, language)
    
    # Construct prompt based on language
    if language == 'ar':
        extract_prompt = f"""استخرج رقم الطلب من رسالة المستخدم التالية. إذا كان هناك رقم طلب، أعد الرقم فقط. إذا لم يكن هناك رقم طلب، أعد 'none'.

سياق المحادثة السابقة:
{conversation_context}

رسالة المستخدم: {user_message}

رقم الطلب:"""
    else:
        extract_prompt = f"""Extract the order number from the following user message. If there is an order number, return only the number. If there is no order number, return 'none'.

Previous conversation context:
{conversation_context}

User message: {user_message}

Order number:"""
    
    # Call LLM to extract order number
    response = llm.invoke(extract_prompt)
    extracted_text = response.content.strip().lower()
    
    # Process the extracted text
    print(f"--- LLM extracted: '{extracted_text}' from message: '{user_message}' ---")
    
    # Check if the extracted text is a valid order number
    if extracted_text == 'none' or not re.search(r'\d+', extracted_text):
        order_number = None
    else:
        # Extract just the numeric part if there's any additional text
        match = re.search(r'(\d+)', extracted_text)
        if match:
            order_number = match.group(1)
        else:
            order_number = None
    
    # Process the order status with the extracted order number
    if order_number:
        return process_order_status(order_number, language)
    else:
        # If no order number found, ask the user to provide one
        if language == 'ar':
            response = "يرجى تقديم رقم الطلب الخاص بك حتى أتمكن من التحقق من حالته."
        else:
            response = "Please provide your order number so I can check its status."
        return {"action_result": {"order_status": {"found": False, "message": response}}}
    
def process_order_status(order_number, language):
    """Process order status for a given order number and language."""
    # Define order statuses for orders 1-5
    order_statuses = {
        "1": {"status": "delivered", "description": "Your order has been delivered successfully.", 
              "ar_description": "تم توصيل طلبك بنجاح."},
        "2": {"status": "shipped", "description": "Your order has been shipped and is on its way to you.", 
              "ar_description": "تم شحن طلبك وهو في الطريق إليك."},
        "3": {"status": "processing", "description": "Your order is currently being processed in our warehouse.", 
              "ar_description": "يتم تجهيز طلبك حاليًا في مستودعنا."},
        "4": {"status": "payment_confirmed", "description": "Payment for your order has been confirmed and we're preparing your items.", 
              "ar_description": "تم تأكيد الدفع لطلبك ونحن نقوم بتجهيز العناصر الخاصة بك."},
        "5": {"status": "pending", "description": "Your order is pending confirmation. We'll update you soon.", 
              "ar_description": "طلبك في انتظار التأكيد. سنقوم بتحديث حالته قريبًا."}
    }
    
    # Check if order number is between 1-5
    if order_number in order_statuses:
        status_info = order_statuses[order_number]
        if language == 'ar':
            response = f"طلبك رقم {order_number} {status_info['ar_description']}"
        else:
            response = f"Order #{order_number} is currently {status_info['status']}. {status_info['description']}"
        
        # Create order info object for display
        order_info = {
            "order_id": order_number,
            "status": status_info['status'],
            "status_description": status_info['description'] if language == 'en' else status_info['ar_description'],
            "estimated_delivery": "2025-05-01" if status_info['status'] in ['processing', 'payment_confirmed', 'shipped'] else None,
            "tracking_number": f"TRK{order_number}12345" if status_info['status'] == 'shipped' else None
        }
        
        return {"action_result": {"order_status": {"found": True, "message": response, "order_info": order_info}}}
    else:
        # Order number not in range 1-5
        if language == 'ar':
            response = f"عذرًا، لا يمكنني العثور على معلومات حول الطلب رقم {order_number}. يرجى التأكد من رقم الطلب والمحاولة مرة أخرى."
        else:
            response = f"Sorry, I couldn't find information for order #{order_number}. Please verify your order number and try again."
        
        return {"action_result": {"order_status": {"found": False, "message": response}}}

def action_node(state: ConversationState):
    """Invokes the appropriate tool based on the classified intent."""
    print("--- Node: Action ---")
    intent = state['intent']
    user_message = state['user_message']
    messages = state['messages']
    db = state.get('db')
    language = state.get('language', 'en')  # Get language from state
    
    # Handle order status queries
    if intent == 'order_status':
        return order_status_node(state)
    
    # Handle coupon queries
    if intent == 'coupon_query':
        if db:
            coupon_result = handle_coupon_query(user_message, db)
            print(f"--- Coupon Query Result: {coupon_result} ---")
            return {"action_result": {"coupon_query": coupon_result}}
        else:
            print("--- No DB session available for coupon query ---")
            return {"action_result": {"coupon_query": {"error": "Database not available"}}}
    
    # Regular tool handling for other intents
    tool_map = {tool.name: tool for tool in tools}
    tool_to_call = None
    
    if intent == 'knowledge_base_query':
        # For other knowledge base queries, try the regular tool
        tool_to_call = tool_map.get('knowledge_base_retriever')
        input_value = user_message  # Use string input instead of state
    elif intent == 'product_availability':
        tool_to_call = tool_map.get('product_availability_checker')
        # For product availability, we need to pass both the message and the database session
        # We'll handle this specially below
        input_value = user_message  # Define input_value for this intent too
    else:
        input_value = user_message

    # If a specific tool is identified for the intent
    if tool_to_call:
        print(f"--- Calling Tool: {tool_to_call.name} with input: {input_value} ---")
        try:
            # For product availability, we need to handle the database session differently
            if intent == 'product_availability' and db:
                print(f"--- Special handling for product availability with DB ---")
                print(f"--- Looking for products in database with query: '{user_message}' ---")
                
                # First, try to get all products if it's a general query
                # English patterns
                english_pattern = re.search(r'what (products|items|do you have|are your products)', user_message.lower())
                # Arabic patterns - matching common ways to ask about products
                # Simplified pattern to match any Arabic query about products
                arabic_pattern = re.search(r'(ما هي|ما|اريد|أريد).*(المنتجات|منتجات|البضائع|بضائع|السلع)', user_message)
                
                # Debug prints
                print(f"--- User message: '{user_message}' ---")
                print(f"--- English pattern match: {english_pattern} ---")
                print(f"--- Arabic pattern match: {arabic_pattern} ---")
                
                # Force Arabic pattern match for testing
                if language == 'ar' and 'منتجات' in user_message:
                    arabic_pattern = True
                
                if english_pattern or arabic_pattern:
                    print("--- General product query detected, retrieving all products ---")
                    from app.services.product import ProductService
                    product_service = ProductService(db)
                    products = product_service.get_products(limit=10)
                    
                    if products and len(products) > 0:
                        print(f"--- Found {len(products)} products in database ---")
                        # Format multiple products
                        product_list = []
                        for p in products:
                            product_list.append({
                                "id": p.id,
                                "name": p.name,
                                "price": p.price,
                                "currency": p.currency,
                                "stock": p.stock_quantity,
                                "category": p.category,
                                "description": p.description or ""
                            })
                        
                        # Return all products found
                        return {"action_result": {
                            "product_availability": {
                                "found": True,
                                "multiple_products": True,
                                "products": product_list,
                                "message": f"Found {len(product_list)} products in our inventory."
                            }
                        }}
                    
                # If not a general query or no products found, try to extract specific product name
                # English patterns
                product_match = re.search(r'(?:do you have|is there|availability of|stock of|looking for)\s+([\w\s]+)(?:\?|$)', user_message.lower())
                if not product_match:
                    # Try a more general pattern
                    product_match = re.search(r'([\w\s]+)(?:\s+in stock|\s+available|\?|$)', user_message.lower())
                
                # Arabic patterns for specific product queries
                if not product_match:
                    # Try to match Arabic patterns like "هل لديكم قميص قطني؟" or "أريد معلومات عن قميص قطني"
                    arabic_product_match = re.search(r'(?:هل لديكم|هل عندكم|هل يوجد|أريد معلومات عن|اريد معلومات عن|معلومات عن)\s+([\w\s]+)(?:\?|$)', user_message)
                    if arabic_product_match:
                        product_match = arabic_product_match
                    else:
                        # Try even more general Arabic pattern
                        arabic_product_match = re.search(r'(?:عن|حول|عندكم|لديكم)\s+([\w\s]+)', user_message)
                        if arabic_product_match:
                            product_match = arabic_product_match
                
                product_name = product_match.group(1).strip() if product_match else user_message
                print(f"--- Extracted product name: '{product_name}' ---")
                
                # Use ProductSearchService directly
                from app.services.product_search import ProductSearchService
                product_search = ProductSearchService(db)
                found, product_info = product_search.search_product_by_name(product_name)
                
                if found:
                    print(f"--- Found product in database: {product_info['name']} ---")
                    product_data = {
                        "found": True,
                        "multiple_products": False,
                        "product": {
                            "product_name": product_info["name"],
                            "availability": "In Stock" if product_info.get("stock_quantity", 0) > 0 else "Out of Stock",
                            "stock": product_info.get("stock_quantity", 0),
                            "price": product_info.get("price", 0),
                            "currency": product_info.get("currency", "USD"),
                            "description": product_info.get("description", ""),
                            "category": product_info.get("category", "")
                        },
                        "message": f"Found product: {product_info['name']} - Price: {product_info.get('price', 0)} {product_info.get('currency', 'USD')}, Stock: {product_info.get('stock_quantity', 0)}"
                    }
                    
                    # Return the action result directly
                    return {"action_result": {"product_availability": product_data}}
                else:
                    print(f"--- No product found in database for: '{product_name}' ---")
                    # Create a standardized observation for no products found
                    product_data = {
                        "found": False,
                        "message": f"I couldn't find any products matching '{product_name}' in our inventory."
                    }
                    
                    # Return the action result directly
                    return {"action_result": {"product_availability": product_data}}
            else:
                # Invoke the tool with the string input for other intents
                observation = tool_to_call.invoke(input_value)
            
            # Special handling for knowledge base retrieval
            if intent == 'knowledge_base_query' and isinstance(observation, str):
                # For knowledge base retriever, we get back a string with the context
                print(f"--- Tool Observation: Knowledge base context retrieved, length: {len(observation)} ---")
                # Return both the action result and the retrieved context
                return {
                    "retrieved_context": observation if observation != "No relevant information found in the knowledge base." else None,
                    "action_result": {intent: {"found": observation != "No relevant information found in the knowledge base."}}
                }
            else:
                # For other tools, handle as before
                # Ensure observation is serializable if it's complex
                if not isinstance(observation, (str, dict, list, int, float, bool, type(None))):
                    observation = str(observation)
                    
                print(f"--- Tool Observation: {observation} ---")
                return {"action_result": {intent: observation}}

        except Exception as e:
            print(f"--- Tool Invocation Error: {e} ---")
            observation = {"error": f"Failed to execute action: {e}"}
            return {"action_result": {intent: observation}}
    else:
        print(f"--- No specific tool for intent '{intent}', skipping action. ---")
        # No specific tool, maybe pass directly to response generation
        return {"action_result": None}

def generate_response_node(state: ConversationState):
    """Generates the final response to the user."""
    print("--- Node: Generate Response ---")
    user_message_content = state['user_message']
    messages = state['messages']
    intent = state['intent']
    context = state.get('retrieved_context')
    action_result = state.get('action_result')
    language = state.get('language', 'en')  # Default to English if not specified
    
    # We won't use session_id in this function anymore
    # The history will be saved in the API endpoint

    # Special handling for order status results
    if intent == 'order_status' and action_result and 'order_status' in action_result:
        order_result = action_result['order_status']
        response_text = order_result['message']
        
        # Add to history
        updated_messages = messages + [HumanMessage(content=user_message_content), AIMessage(content=response_text)]
        
        # If order was found, include order_info in the return value
        if order_result.get('found', False) and 'order_info' in order_result:
            return {"response": response_text, "order_info": order_result['order_info'], "messages": updated_messages}
        else:
            return {"response": response_text, "messages": updated_messages}
    
    # Special handling for product availability results
    if intent == 'product_availability' and action_result and 'product_availability' in action_result:
        product_result = action_result['product_availability']
        
        # Check if we found multiple products
        if product_result.get('multiple_products', False) and 'products' in product_result:
            products = product_result['products']
            if language == 'ar':
                response_text = "لقد وجدت المنتجات التالية في مخزوننا:\n\n"
            else:
                response_text = "I found the following products in our inventory:\n\n"
                
            # Format product list
            for i, product in enumerate(products, 1):
                if language == 'ar':
                    response_text += f"{i}. {product['name']} - {product['price']} {product['currency']} - "
                    response_text += "متوفر" if product['stock'] > 0 else "غير متوفر"
                    if product['description']:
                        response_text += f" - {product['description']}"
                    response_text += "\n"
                else:
                    response_text += f"{i}. {product['name']} - {product['price']} {product['currency']} - "
                    response_text += "In Stock" if product['stock'] > 0 else "Out of Stock"
                    if product['description']:
                        response_text += f" - {product['description']}"
                    response_text += "\n"
            
            if language == 'ar':
                response_text += "\nهل ترغب في معرفة المزيد عن أي من هذه المنتجات؟"
            else:
                response_text += "\nWould you like to know more about any of these products?"
                
            # Add to history - using messages from state
            updated_messages = messages + [HumanMessage(content=user_message_content), AIMessage(content=response_text)]
            # Return the updated messages to be saved in the API endpoint
            
            return {"response": response_text, "products": products, "messages": updated_messages}
            
        # Check if we found a specific product
        elif product_result.get('found', False) and 'product' in product_result:
            product = product_result['product']
            
            if language == 'ar':
                if product.get('stock', 0) > 0:
                    response_text = f"نعم، لدينا {product['product_name']} في المخزون! يوجد حاليًا {product['stock']} وحدة متاحة بسعر {product['price']} {product.get('currency', 'USD')}."
                else:
                    response_text = f"عذرًا، {product['product_name']} غير متوفر حاليًا. هل ترغب في إشعارك عندما يكون متاحًا مرة أخرى؟"
            else:
                if product.get('stock', 0) > 0:
                    response_text = f"Yes, we have {product['product_name']} in stock! There are currently {product['stock']} units available at {product['price']} {product.get('currency', 'USD')}."
                else:
                    response_text = f"I'm sorry, but {product['product_name']} is currently out of stock. Would you like me to notify you when it's back in stock?"
            
            # Add description if available
            if product.get('description') and product['description'].strip():
                if language == 'ar':
                    response_text += f"\n\nوصف المنتج: {product['description']}"
                else:
                    response_text += f"\n\nProduct description: {product['description']}"
            
            # Add to history - using messages from state
            updated_messages = messages + [HumanMessage(content=user_message_content), AIMessage(content=response_text)]
            # Return the updated messages to be saved in the API endpoint
            
            return {"response": response_text, "product": product, "messages": updated_messages}
        
        # No products found
        elif not product_result.get('found', False):
            if language == 'ar':
                response_text = "عذرًا، لم أتمكن من العثور على أي منتجات تطابق طلبك. هل يمكنك تحديد ما تبحث عنه بشكل أكثر تفصيلاً؟"
            else:
                response_text = "I'm sorry, I couldn't find any products matching your request. Could you please specify what you're looking for in more detail?"
            
            # Add to history - using messages from state
            updated_messages = messages + [HumanMessage(content=user_message_content), AIMessage(content=response_text)]
            # Return the updated messages to be saved in the API endpoint
            
            return {"response": response_text, "messages": updated_messages}
    
    # Regular handling for other intents
    # Prepare prompt for LLM
    prompt_context = ""
    if context:
        prompt_context += f"\n\nRelevant Information from Knowledge Base:\n{context}"
    if action_result:
        # Convert dict result to string for the prompt
        action_result_str = json.dumps(action_result, indent=2)
        prompt_context += f"\n\nResult from Action ({intent}):\n{action_result_str}"

    # Add the current user message to the history for the LLM call
    current_history = messages + [HumanMessage(content=user_message_content)]

    # Construct the prompt
    prompt = f"""You are a helpful e-commerce customer support assistant.
    Answer the user's query based on the conversation history and the provided context or action results.
    Be concise and helpful. If you performed an action, summarize the result clearly.
    If relevant information was found in the knowledge base, use it to answer.
    If the intent was a greeting, respond politely.
    
    Remember to support both English and Arabic languages. If the user's message is in Arabic, respond in Arabic.
    If you cannot answer, politely say so.

    Conversation History:
    {[f'{m.type}: {m.content}' for m in current_history]}
    {prompt_context}

    Assistant Response:"""

    print(f"--- Generating response with prompt: {prompt[:300]}... ---")

    # Invoke the main LLM
    response = llm.invoke(prompt)
    ai_response_content = response.content

    print(f"--- Generated AI Response: {ai_response_content} ---")

    # Add the AI response to the message history
    updated_messages = current_history + [AIMessage(content=ai_response_content)]

    return {"messages": updated_messages}

def handle_coupon_query(user_message: str, db: Session):
    """Handles coupon-related queries by checking for specific coupon codes or listing all active coupons."""
    # Initialize the coupon service
    coupon_service = CouponService(db)
    
    # Check if the user is asking for a specific coupon code
    code_match = re.search(r'coupon\s+(?:code\s+)?([A-Za-z0-9]+)', user_message, re.IGNORECASE)
    
    if code_match:
        # User is asking about a specific coupon code
        code = code_match.group(1).upper()
        coupon = coupon_service.get_coupon_by_code(code)
        
        if coupon:
            # Format the coupon for response
            formatted_coupon = {
                "code": coupon.code,
                "discount": coupon.discount,
                "description": coupon.description or "",
                "expires_at": coupon.expires_at.isoformat() if coupon.expires_at else None,
                "is_active": coupon.is_active
            }
            
            return {"coupon": formatted_coupon, "message": coupon_service.format_coupon_for_display(coupon)}
        else:
            return {"error": f"No coupon found with code '{code}'"}
    
    # User is asking for available coupons
    active_coupons = coupon_service.get_active_coupons()
    formatted_coupons = []
    
    for coupon in active_coupons:
        formatted_coupons.append({
            "code": coupon.code,
            "discount": coupon.discount,
            "description": coupon.description or "",
            "expires_at": coupon.expires_at.isoformat() if coupon.expires_at else None,
            "is_active": coupon.is_active
        })
    
    return {
        "coupons": formatted_coupons,
        "message": coupon_service.format_coupons_list(active_coupons)
    }
