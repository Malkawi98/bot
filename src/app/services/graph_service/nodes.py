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

# Define the edges for the graph flow
from .edges import route_based_on_intent


# This function is no longer needed as we use LLM-based frustration detection
# Keeping it for backward compatibility
def detect_frustration(user_message: str) -> bool:
    # This is now handled by the LLM in classify_intent_node
    return False


def frustration_node(state: ConversationState):
    """Handles user frustration using LLM to generate an empathetic response and offer appropriate help."""
    print("--- Node: Frustration ---")
    user_message = state['user_message']
    messages = state['messages']
    frustration_count = state.get('frustration_count', 0)
    language = state.get('language', 'en')
    
    # Create a history string for context
    history_str = "\n".join([f"{m.type}: {m.content}" for m in messages[-5:]])  # Last 5 messages for context
    
    # Create a prompt for the LLM to generate an empathetic response
    prompt = f"""You are a helpful customer service AI for an e-commerce store.
    The user is showing signs of frustration. Based on the conversation history and their message,
    generate an empathetic response that acknowledges their frustration and offers appropriate help.
    
    Conversation History:
    {history_str}
    
    User's Message: "{user_message}"
    
    Frustration Level: {'High' if frustration_count > 1 else 'Moderate'}
    
    Guidelines:
    1. Be empathetic and acknowledge their feelings
    2. Offer specific help based on what they're trying to accomplish
    3. If frustration level is High, offer to connect them with a human agent
    4. Keep your response concise and helpful
    5. Don't apologize excessively
    
    Your response:
    """
    
    # Use the LLM to generate a response
    response = llm.invoke(prompt)
    
    # Set the bot message to the LLM's response
    state['bot_message'] = response.content.strip()
    
    # If frustration count is high, mark for potential human handoff
    if frustration_count > 2:
        state['potential_human_handoff'] = True
        
    return state


def manager_approval_node(state: ConversationState):
    """Handles requests that require manager approval, such as refunds, using LLM to generate a contextual response."""
    print("--- Node: Manager Approval ---")
    user_message = state['user_message']
    messages = state['messages']
    language = state.get('language', 'en')
    intent = state.get('intent', 'refund_request')
    
    # Create a history string for context
    history_str = "\n".join([f"{m.type}: {m.content}" for m in messages[-5:]])  # Last 5 messages for context
    
    # Use LLM to analyze the refund request and generate an appropriate response
    prompt = f"""You are a helpful customer service AI for an e-commerce store.
    The user has made a request that requires manager approval (likely a refund or special discount).
    
    Conversation History:
    {history_str}
    
    User's Message: "{user_message}"
    
    Request Type: {intent}
    
    Task:
    Generate a response that:
    1. Acknowledges their request specifically
    2. Explains that this type of request requires manager approval
    3. Informs them that Ahmad (the manager) will be notified
    4. Sets clear expectations about next steps and timing
    5. Is professional but empathetic
    
    Your response:
    """
    
    # Use the LLM to generate a response
    response = llm.invoke(prompt)
    
    # Set the bot message to the LLM's response
    state['bot_message'] = response.content.strip()
    state['manager_approval_required'] = True
    
    # Extract and store details about the refund request for the manager
    try:
        # Use LLM to extract key details about the refund request
        details_prompt = f"""Extract key details about this refund or special request:
        
        User's Message: "{user_message}"
        
        Extract and format as JSON with these fields:
        - request_type: The specific type of request (e.g., "refund", "discount", "exception")
        - reason: The reason given for the request
        - order_id: Any order ID mentioned (or null if none)
        - product: Any product mentioned (or null if none)
        - urgency: Estimated urgency level ("low", "medium", "high")
        
        JSON response:
        """
        
        details_response = classifier_llm.invoke(details_prompt)
        
        try:
            request_details = json.loads(details_response.content.strip())
            state['request_details'] = request_details
        except json.JSONDecodeError:
            # Fallback if response isn't valid JSON
            state['request_details'] = {
                "request_type": intent,
                "raw_message": user_message
            }
    except Exception as e:
        print(f"Error extracting request details: {e}")
        # Simple fallback
        state['request_details'] = {
            "request_type": intent,
            "raw_message": user_message
        }
    
    return state


# Define frustration detection functions
# We'll use these in the classify_intent_node function

def classify_intent_node(state: ConversationState):
    """Classifies the user's intent based on the latest message and detects frustration."""
    print("--- Node: Classify Intent ---")
    user_message = state['user_message']
    messages = state['messages']
    language = state.get('language', 'en')  # Get language from state
    
    # Create a history string for the LLM prompt
    history_str = "\n".join([f"{m.type}: {m.content}" for m in messages])
    
    # Define possible intents including coupon_query
    possible_intents = "'order_status', 'knowledge_base_query', 'product_availability', 'coupon_query', 'greeting', 'refund_request', 'other'"
    
    # Create a comprehensive prompt for the LLM to classify intent and detect frustration
    prompt = f"""Analyze the following user message in the context of the conversation history.
    Conversation History:
    {history_str}
    
    User Message: "{user_message}"
    
    Tasks:
    1. Classify the user's primary intent. Choose ONE from the following list: {possible_intents}.
    2. Determine if the user is expressing significant frustration (e.g., anger, annoyance, dissatisfaction). Answer 'yes' or 'no'.
    
    Format your response as a JSON object with two fields: 'intent' and 'is_frustrated'.
    Example: {{'intent': 'product_availability', 'is_frustrated': 'no'}}
    """

    # Use the classifier LLM to analyze the message
    response = classifier_llm.invoke(prompt)
    response_content = response.content.strip()
    
    try:
        # Parse the JSON response
        result = json.loads(response_content)
        intent = result.get('intent', '').lower()
        is_frustrated = result.get('is_frustrated', 'no').lower() == 'yes'
    except json.JSONDecodeError:
        # Fallback if response is not valid JSON
        print(f"--- Failed to parse LLM response as JSON: {response_content} ---")
        intent = 'knowledge_base_query'  # Default fallback
        is_frustrated = False
    
    # Basic validation/cleanup
    allowed_intents = ['order_status', 'knowledge_base_query', 'product_availability', 'coupon_query', 'greeting', 'refund_request', 'other']
    if intent not in allowed_intents:
        print(f"--- Classified intent '{intent}' not in allowed list, defaulting to 'knowledge_base_query'. ---")
        intent = 'knowledge_base_query'
    
    print(f"--- Classified Intent: {intent} ---")
    print(f"--- Frustration Detected: {is_frustrated} ---")
    
    # Handle special cases using LLM for more accurate detection
    if intent == 'refund_request':
        print("--- Detected refund request, routing to manager approval ---")
        # Use LLM to verify this is indeed a refund request that needs approval
        verification_prompt = f"""Analyze this user message and determine if it's a refund request that requires manager approval.
        
        User Message: "{user_message}"
        
        Consider:
        1. Is the user explicitly asking for a refund?
        2. Are they describing a problem that would typically result in a refund?
        3. Is the request complex or outside standard policy?
        
        Answer with only 'yes' if manager approval is needed, or 'no' if this can be handled by automated systems.
        """
        
        verification_response = classifier_llm.invoke(verification_prompt)
        needs_approval = verification_response.content.strip().lower() == 'yes'
        
        if needs_approval:
            return {"intent": "manager_approval"}
        else:
            # If it's a simpler refund request that doesn't need approval
            print("--- Refund request can be handled automatically ---")
            return {"intent": "knowledge_base_query"}
    
    # Track frustration count
    frustration_count = state.get('frustration_count', 0)
    if is_frustrated or intent == 'other':
        frustration_count += 1
        state['frustration_count'] = frustration_count
        print(f"--- Incremented frustration. New count: {frustration_count} ---")
    
    return {"intent": intent, "frustration_count": frustration_count}


def order_status_node(state: ConversationState):
    """Handles order status queries and provides status information for orders 1-5."""
    print("--- Node: Order Status ---")
    user_message = state['user_message']
    messages = state['messages']
    language = state.get('language', 'en')  # Get language from state

    # Check if order number was already extracted in the entity extraction node
    extracted_order_number = state.get('extracted_order_number')
    if extracted_order_number and extracted_order_number != 'unknown':
        print(f"--- Using extracted order number: {extracted_order_number} ---")
        return process_order_status(extracted_order_number, language)
    # If no order number was extracted, ask the user to provide one
    if language == 'ar':
        response = "يرجى تقديم رقم الطلب الخاص بك حتى أتمكن من التحقق من حالته."
    else:
        response = "Please provide your order number so I can check its status."

    return {"action_result": {"order_status": {"found": False, "message": response}}}


def process_order_status(order_number, language):
    """Process order status for a given order number and language."""
    # Mock order status data - in a real app, this would query a database
    orders = {
        "1": {"status": "shipped", "estimated_delivery": "2023-04-15", "tracking_number": "TN12345678"},
        "2": {"status": "processing", "estimated_ship_date": "2023-04-10"},
        "3": {"status": "delivered", "delivery_date": "2023-04-01"},
        "4": {"status": "cancelled", "cancel_reason": "customer request"},
        "5": {"status": "pending", "payment_status": "awaiting payment"}
    }
    
    # Check if the order exists
    if order_number in orders:
        order = orders[order_number]
        status = order["status"]
        
        # Format the response based on the order status and language
        if language == "ar":
            # Arabic responses
            if status == "shipped":
                response = f"تم شحن طلبك رقم {order_number}. رقم التتبع الخاص بك هو {order['tracking_number']}. تاريخ التسليم المتوقع هو {order['estimated_delivery']}."
            elif status == "processing":
                response = f"طلبك رقم {order_number} قيد المعالجة. تاريخ الشحن المتوقع هو {order['estimated_ship_date']}."
            elif status == "delivered":
                response = f"تم تسليم طلبك رقم {order_number} في {order['delivery_date']}."
            elif status == "cancelled":
                response = f"تم إلغاء طلبك رقم {order_number}. السبب: {order['cancel_reason']}."
            elif status == "pending":
                response = f"طلبك رقم {order_number} معلق. حالة الدفع: {order['payment_status']}."
            else:
                response = f"حالة طلبك رقم {order_number} هي: {status}."
        else:
            # English responses (default)
            if status == "shipped":
                response = f"Your order #{order_number} has been shipped. Your tracking number is {order['tracking_number']}. Estimated delivery date is {order['estimated_delivery']}."
            elif status == "processing":
                response = f"Your order #{order_number} is being processed. Estimated ship date is {order['estimated_ship_date']}."
            elif status == "delivered":
                response = f"Your order #{order_number} was delivered on {order['delivery_date']}."
            elif status == "cancelled":
                response = f"Your order #{order_number} has been cancelled. Reason: {order['cancel_reason']}."
            elif status == "pending":
                response = f"Your order #{order_number} is pending. Payment status: {order['payment_status']}."
            else:
                response = f"The status of your order #{order_number} is: {status}."
        
        return {"action_result": {"order_status": {"found": True, "status": status, "message": response}}}
    else:
        # Order not found
        if language == "ar":
            response = f"عذراً، لم أتمكن من العثور على معلومات للطلب رقم {order_number}. يرجى التحقق من رقم الطلب والمحاولة مرة أخرى."
        else:
            response = f"Sorry, I couldn't find information for order #{order_number}. Please verify your order number and try again."

        return {"action_result": {"order_status": {"found": False, "message": response}}}


def action_node(state: ConversationState):
    """Invokes the appropriate tool based on the classified intent and extracted entities."""
    print("--- Node: Action ---")
    user_message = state['user_message']
    intent = state.get('intent')
    extracted_entity = state.get('extracted_entity')
    entity_type = state.get('entity_type')
    language = state.get('language', 'en')  # Default to English if not set
    mild_frustration = state.get('mild_frustration', False)  # Check if user has mild frustration
    
    # First, extract necessary entities based on intent
    entity_result = decide_tool_or_fetch_data_node(state)
    extracted_entity = entity_result.get('extracted_entity')
    entity_type = entity_result.get('entity_type')
    
    print(f"--- Extracted Entity: {extracted_entity} (Type: {entity_type}) ---")
    
    # Handle order status queries
    if intent == 'order_status':
        # Update state with extracted order number if available
        if entity_type == 'order_number' and extracted_entity != 'unknown':
            state['extracted_order_number'] = extracted_entity
        return order_status_node(state)

    # Handle coupon queries with LLM-based entity extraction
    if intent == 'coupon_query':
        if db:
            # Pass the extracted coupon code to the handle_coupon_query function
            coupon_code = extracted_entity if entity_type == 'coupon_code' else None
            coupon_result = handle_coupon_query(user_message, db, coupon_code)
            print(f"--- Coupon Query Result: {coupon_result} ---")
            return {"action_result": {"coupon_query": coupon_result}}
        else:
            print("--- No DB session available for coupon query ---")
            return {"action_result": {"coupon_query": {"error": "Database not available"}}}

    # Regular tool handling for other intents
    tool_map = {tool.name: tool for tool in tools}
    tool_to_call = None

    if intent == 'knowledge_base_query' or intent == 'other':
        print("--- Using RAG tool for knowledge base query ---")
        # Use the RAG tool to search for relevant information
        try:
            from app.services.rag import search_knowledge_base
            from app.db.session import get_db
            db = next(get_db())
            
            # If there's mild frustration, use LLM to reformulate the query for better results
            if mild_frustration:
                print("--- Detected mild frustration, reformulating query for better results ---")
                reformulation_prompt = f"""The user seems slightly frustrated with their query: "{user_message}"
                
                Please reformulate this into a clear, neutral search query that will help find the most relevant information.
                Keep it concise and focused on the core information need.
                
                Reformulated query:
                """
                
                reformulation_response = classifier_llm.invoke(reformulation_prompt)
                reformulated_query = reformulation_response.content.strip()
                print(f"--- Reformulated query: '{reformulated_query}' ---")
                
                # Search with both the original and reformulated queries for better coverage
                results_original = search_knowledge_base(user_message, db, language=language)
                results_reformulated = search_knowledge_base(reformulated_query, db, language=language)
                
                # Combine and deduplicate results
                seen_ids = set()
                combined_results = []
                
                # Process original results first (they might be more directly relevant)
                for result in results_original:
                    result_id = result.get("id")
                    if result_id not in seen_ids:
                        seen_ids.add(result_id)
                        combined_results.append(result)
                
                # Then add unique reformulated results
                for result in results_reformulated:
                    result_id = result.get("id")
                    if result_id not in seen_ids:
                        seen_ids.add(result_id)
                        combined_results.append(result)
                
                results = combined_results
            else:
                # Standard search without reformulation
                results = search_knowledge_base(user_message, db, language=language)
            
            if results and len(results) > 0:
                # Store the search results in the state
                state['kb_results'] = results
                print(f"--- Found {len(results)} relevant knowledge base entries ---")
                
                # Format the results for display
                formatted_results = []
                for result in results:
                    formatted_results.append({
                        "title": result.get("title", "Untitled"),
                        "content": result.get("content", ""),
                        "score": result.get("score", 0.0)
                    })
                    
                state['kb_formatted_results'] = formatted_results
            else:
                print("--- No relevant knowledge base entries found ---")
                state['kb_results'] = []
                state['kb_formatted_results'] = []
        except Exception as e:
            print(f"--- Error searching knowledge base: {e} ---")
            state['kb_results'] = []
            state['kb_formatted_results'] = []
    elif intent == 'product_availability':
        tool_to_call = tool_map.get('product_availability_checker')
        # For product availability, we'll use the extracted product name
        input_value = extracted_entity if entity_type == 'product_name' else user_message
    else:
        input_value = user_message

    # If a specific tool is identified for the intent
    if tool_to_call:
        print(f"--- Calling Tool: {tool_to_call.name} with input: {input_value} ---")
        try:
            # For product availability, we need to handle the database session differently
            if intent == 'product_availability' and db:
                print(f"--- Special handling for product availability with DB ---")
                print(f"--- Looking for products in database with query: '{input_value}' ---")
                
                # Use the extracted product name from LLM
                product_name = input_value
                if product_name == "general product query":
                    # Handle general product queries differently if needed
                    print("--- General product query detected ---")

                # Use ProductSearchService directly
                from app.services.product_search import ProductSearchService
                product_search = ProductSearchService(db)
                print(f"--- Searching for product: '{product_name}' ---")
                found, product_info = product_search.search_product_by_name(product_name)
                print(f"--- Search result: found={found}, product_info={product_info} ---")

                if found:
                    print(f"--- Found product in database: {product_info['name']} ---")
                    product_data = {"found": True, "multiple_products": False,
                                    "product": {"product_name": product_info["name"],
                                                "availability": "In Stock" if product_info.get(
                                                    "stock_quantity", 0) > 0 else "Out of Stock",
                                                "stock": product_info.get("stock_quantity", 0),
                                                "price": product_info.get("price", 0),
                                                "currency": product_info.get("currency", "USD"),
                                                "description": product_info.get("description", ""),
                                                "category": product_info.get("category", "")},
                                    "message": f"Found product: {product_info['name']} - Price: {product_info.get('price', 0)} {product_info.get('currency', 'USD')}, Stock: {product_info.get('stock_quantity', 0)}"}

                    # Return the action result directly
                    return {"action_result": {"product_availability": product_data}}
                else:
                    print(f"--- No product found in database for: '{product_name}' ---")
                    # Create a standardized observation for no products found
                    product_data = {"found": False, "message": f"No, we don't sell {product_name}."}

                    # Return the action result directly
                    return {"action_result": {"product_availability": product_data}}
            else:
                # Invoke the tool with the string input for other intents
                observation = tool_to_call.invoke(input_value)

            # Special handling for knowledge base retrieval
            if intent == 'knowledge_base_query' and isinstance(observation, str):
                # For knowledge base retriever, we get back a string with the context
                print(
                    f"--- Tool Observation: Knowledge base context retrieved, length: {len(observation)} ---")
                # Return both the action result and the retrieved context
                return {
                    "retrieved_context": observation if observation != "No relevant information found in the knowledge base." else None,
                    "action_result": {intent: {
                        "found": observation != "No relevant information found in the knowledge base."}}}
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
        updated_messages = messages + [HumanMessage(content=user_message_content),
                                       AIMessage(content=response_text)]

        # If order was found, include order_info in the return value
        if order_result.get('found', False) and 'order_info' in order_result:
            return {"response": response_text, "order_info": order_result['order_info'],
                    "messages": updated_messages}
        else:
            return {"response": response_text, "messages": updated_messages}

    # Special handling for coupon query results
    if intent == 'coupon_query' and action_result and 'coupon_query' in action_result:
        coupon_result = action_result['coupon_query']
        query_type = coupon_result.get('query_type', 'general_query')
        
        # Handle specific coupon code queries
        if query_type == 'specific_code':
            if coupon_result.get('found', False) and 'coupon' in coupon_result:
                coupon = coupon_result['coupon']
                if language == 'ar':
                    response_text = f"نعم، لدينا كوبون {coupon['code']}! يمنحك خصمًا بنسبة {coupon['discount']}%."
                    if coupon.get('description'):
                        response_text += f" {coupon['description']}"
                    if coupon.get('expires_at'):
                        response_text += f" هذا الكوبون صالح حتى {coupon['expires_at']}."
                else:
                    response_text = f"Yes, we have the coupon {coupon['code']}! It gives you a {coupon['discount']}% discount."
                    if coupon.get('description'):
                        response_text += f" {coupon['description']}"
                    if coupon.get('expires_at'):
                        response_text += f" This coupon is valid until {coupon['expires_at']}."
            else:
                # Coupon code not found
                code = coupon_result.get('code', '')
                if language == 'ar':
                    response_text = f"عذرًا، الكوبون {code} غير صالح أو غير متوفر. الرجاء التحقق من الرمز والمحاولة مرة أخرى، أو اسأل عن الكوبونات المتاحة لدينا."
                else:
                    response_text = f"Sorry, the coupon {code} is invalid or unavailable. Please check the code and try again, or ask about our available coupons."
        
        # Handle list all coupons queries
        elif query_type == 'list_all':
            if coupon_result.get('found', False) and 'coupons' in coupon_result and len(coupon_result['coupons']) > 0:
                coupons = coupon_result['coupons']
                if language == 'ar':
                    response_text = "هذه هي الكوبونات المتاحة حاليًا:\n\n"
                else:
                    response_text = "Here are our currently available coupons:\n\n"
                
                for i, coupon in enumerate(coupons, 1):
                    if language == 'ar':
                        response_text += f"{i}. {coupon['code']} - خصم {coupon['discount']}%"
                        if coupon.get('description'):
                            response_text += f" - {coupon['description']}"
                        if coupon.get('expires_at'):
                            response_text += f" (صالح حتى {coupon['expires_at']})"
                    else:
                        response_text += f"{i}. {coupon['code']} - {coupon['discount']}% discount"
                        if coupon.get('description'):
                            response_text += f" - {coupon['description']}"
                        if coupon.get('expires_at'):
                            response_text += f" (valid until {coupon['expires_at']})"
                    response_text += "\n"
            else:
                # No coupons available
                if language == 'ar':
                    response_text = "عذرًا، ليس لدينا أي كوبونات متاحة حاليًا. يرجى التحقق مرة أخرى في وقت لاحق."
                else:
                    response_text = "Sorry, we don't have any coupons available at the moment. Please check back later."
        
        # Handle general coupon queries
        else:  # general_query
            has_coupons = coupon_result.get('has_coupons', False)
            if has_coupons:
                count = coupon_result.get('count', 0)
                if language == 'ar':
                    response_text = f"نعم، لدينا {count} كوبون(ات) متاحة حاليًا. هل ترغب في معرفة التفاصيل؟"
                else:
                    response_text = f"Yes, we have {count} coupon(s) available right now. Would you like to know the details?"
            else:
                if language == 'ar':
                    response_text = "عذرًا، ليس لدينا أي كوبونات متاحة حاليًا. يرجى التحقق مرة أخرى في وقت لاحق."
                else:
                    response_text = "Sorry, we don't have any coupons available at the moment. Please check back later."
        
        # Add to history
        updated_messages = messages + [HumanMessage(content=user_message_content),
                                      AIMessage(content=response_text)]
        
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
            updated_messages = messages + [HumanMessage(content=user_message_content),
                                           AIMessage(content=response_text)]
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
            updated_messages = messages + [HumanMessage(content=user_message_content),
                                           AIMessage(content=response_text)]
            # Return the updated messages to be saved in the API endpoint

            return {"response": response_text, "product": product, "messages": updated_messages}

        # No products found
        elif not product_result.get('found', False):
            # Use the message from the product_result if available
            if 'message' in product_result:
                response_text = product_result['message']
            else:
                if language == 'ar':
                    response_text = "عذرًا، لا نبيع هذا المنتج."
                else:
                    response_text = "No, we don't sell this product."

            # Add to history - using messages from state
            updated_messages = messages + [HumanMessage(content=user_message_content),
                                           AIMessage(content=response_text)]
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


def decide_tool_or_fetch_data_node(state: ConversationState):
    """Uses LLM to extract necessary entities based on the classified intent."""
    print("--- Node: Decide Tool or Fetch Data ---")
    user_message = state['user_message']
    intent = state['intent']
    messages = state['messages']
    language = state.get('language', 'en')  # Get language from state
    frustration_count = state.get('frustration_count', 0)
    
    # Create a base state dictionary with all required fields
    result_state = {
        'user_message': user_message,
        'intent': intent,
        'messages': messages,
        'language': language,
        'frustration_count': frustration_count
    }
    
    # Different entity extraction based on intent
    if intent == 'product_availability':
        # Extract product name from user message
        prompt = f"""Extract the product name from the following user message. 
        The user is asking about product availability.
        
        User message: "{user_message}"
        
        Return ONLY the product name as a simple string, without any additional text, quotes, or formatting.
        If no specific product is mentioned, return "general product query".
        """
        
        response = classifier_llm.invoke(prompt)
        product_name = response.content.strip()
        print(f"--- Extracted product name: '{product_name}' ---")
        
        # Add the extracted entity to the state
        result_state['extracted_entity'] = product_name
        result_state['entity_type'] = "product_name"
        return result_state
        
    elif intent == 'order_status':
        # Extract order number from user message
        prompt = f"""Extract the order number from the following user message.
        The user is asking about order status.
        
        User message: "{user_message}"
        
        Return ONLY the order number as a simple string, without any additional text or formatting.
        If the message contains just a number, that's likely the order number.
        If no order number is mentioned, return "unknown".
        """
        
        response = classifier_llm.invoke(prompt)
        order_number = response.content.strip()
        
        # If the response is just a number, use it directly
        if order_number.isdigit():
            print(f"--- Extracted order number: '{order_number}' ---")
            result_state['extracted_entity'] = order_number
            result_state['entity_type'] = "order_number"
            result_state['extracted_order_number'] = order_number
        else:
            # Check if the user message itself is just a number
            if user_message.strip().isdigit():
                order_number = user_message.strip()
                print(f"--- Using user message as order number: '{order_number}' ---")
                result_state['extracted_entity'] = order_number
                result_state['entity_type'] = "order_number"
                result_state['extracted_order_number'] = order_number
            else:
                print("--- Could not extract order number ---")
                result_state['extracted_entity'] = "unknown"
                result_state['entity_type'] = "order_number"
        
        return result_state
                
    elif intent == 'coupon_query':
        # Extract coupon code from user message with improved guidance
        prompt = f"""Extract the coupon code from the following user message, if one exists.
        The user is asking about a coupon or discount.
        
        User message: "{user_message}"
        
        Guidelines for extraction:
        1. A coupon code is typically a specific promotional code like SUMMER20, DISCOUNT50, etc.
        2. Common English words (like CAN, GET, HAVE, etc.) are NOT coupon codes.
        3. If the user is asking about what coupons are available or what discounts they can get, there is NO specific coupon code.
        4. Only extract a code if the user is explicitly referring to a specific coupon code.
        
        Your response should be ONE of these options:
        - If a specific coupon code is mentioned, return ONLY that code in uppercase
        - If the user is asking about available coupons or what coupons they can get, return "LIST_ALL"
        - If the user is asking a general question about coupons without mentioning a specific code, return "GENERAL_COUPON_QUERY"
        
        Examples:
        - "Do you have a SUMMER20 coupon?" → "SUMMER20"
        - "What coupons do you have?" → "LIST_ALL"
        - "Can I get a discount?" → "GENERAL_COUPON_QUERY"
        - "What coupon can I get from you?" → "LIST_ALL"
        """
        
        response = classifier_llm.invoke(prompt)
        coupon_code = response.content.strip().upper()
        print(f"--- Extracted coupon code or query type: '{coupon_code}' ---")
        
        # Additional validation to prevent common words from being treated as coupon codes
        common_words = ["CAN", "GET", "HAVE", "THE", "FOR", "YOU", "ARE", "ANY", "WHAT", "HOW"]
        if coupon_code in common_words:
            print(f"--- '{coupon_code}' is a common word, treating as general query ---")
            coupon_code = "GENERAL_COUPON_QUERY"
        
        result_state['extracted_entity'] = coupon_code
        result_state['entity_type'] = "coupon_code"
        return result_state
    
    # Default case for other intents
    result_state['extracted_entity'] = None
    result_state['entity_type'] = None
    return result_state


def handle_coupon_query(user_message: str, db: Session, coupon_code=None):
    """Handles coupon-related queries by checking for specific coupon codes or listing all active coupons.
    Now supports LLM-based entity extraction through the coupon_code parameter."""
    # Initialize the coupon service
    coupon_service = CouponService(db)
    language = 'en'  # Default to English, could be extracted from state if needed
    
    print(f"--- Handling coupon query with extracted code: '{coupon_code}' ---")
    
    # If a specific coupon code was extracted by the LLM
    if coupon_code and coupon_code not in ["LIST_ALL", "GENERAL_COUPON_QUERY"]:
        # User is asking about a specific coupon code
        coupon = coupon_service.get_coupon_by_code(coupon_code)

        if coupon:
            # Format the coupon for response
            formatted_coupon = {"code": coupon.code, "discount": coupon.discount,
                                "description": coupon.description or "",
                                "expires_at": coupon.expires_at.isoformat() if coupon.expires_at else None,
                                "is_active": coupon.is_active}

            return {"coupon": formatted_coupon,
                    "message": coupon_service.format_coupon_for_display(coupon),
                    "query_type": "specific_code",
                    "found": True}
        else:
            # No valid coupon found with this code
            return {"error": f"No coupon found with code '{coupon_code}'",
                    "query_type": "specific_code",
                    "found": False,
                    "code": coupon_code}
    
    # User is asking for a list of available coupons
    elif coupon_code == "LIST_ALL":
        active_coupons = coupon_service.get_active_coupons()
        formatted_coupons = []

        for coupon in active_coupons:
            formatted_coupons.append({"code": coupon.code, "discount": coupon.discount,
                                      "description": coupon.description or "",
                                      "expires_at": coupon.expires_at.isoformat() if coupon.expires_at else None,
                                      "is_active": coupon.is_active})

        return {"coupons": formatted_coupons,
                "message": coupon_service.format_coupons_list(active_coupons),
                "query_type": "list_all",
                "found": len(formatted_coupons) > 0,
                "count": len(formatted_coupons)}
    
    # User is asking a general question about coupons
    else:  # GENERAL_COUPON_QUERY or None
        active_coupons = coupon_service.get_active_coupons()
        has_coupons = len(active_coupons) > 0
        
        # For general queries, we'll return information about whether we have coupons
        # but not necessarily list all of them
        return {"has_coupons": has_coupons,
                "count": len(active_coupons),
                "query_type": "general_query",
                "found": has_coupons}
