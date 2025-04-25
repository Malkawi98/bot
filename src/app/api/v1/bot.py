from fastapi import APIRouter, Depends, HTTPException, Response, status, Query, Request, Cookie
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from fastapi.templating import Jinja2Templates
from uuid import uuid4
import json
import random
from datetime import datetime, timedelta
from app.services.rag import RAGService
from app.services.graph_service.graph import graph_app
from app.services.graph_service.state import ConversationState
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from app.core.bot_settings import get_bot_settings_model
from app.core.db.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(tags=["bot"])

# Change template directory for Docker compatibility
templates = Jinja2Templates(directory="/code/app/templates")

# Initialize RAG service
rag_service = RAGService()

# In-memory session state (for demo only)
session_states = {}

# In-memory session store for LangGraph (for demo only)
langraph_session_store: Dict[str, List[Dict]] = {}

# In-memory product catalog (for demo only)
product_catalog = {}

# Enhanced FAQ database with more detailed information
FAQS = {
    "shipping": "We offer free shipping on orders over $50. Standard shipping takes 3-5 business days. Express shipping is available for $9.99 and delivers within 1-2 business days. International shipping varies by country.",
    "return": "You can return any item within 30 days for a full refund. Returns are free if the item is defective or we made a mistake. Otherwise, a $5 return shipping fee applies. Gift returns receive store credit.",
    "payment": "We accept Visa, MasterCard, American Express, Discover, PayPal, Apple Pay, and Google Pay. All transactions are secure and encrypted. We also offer financing options for purchases over $200.",
    "warranty": "All electronics come with a 1-year manufacturer warranty. Extended warranties are available for purchase. Warranty claims require proof of purchase and the original packaging if possible.",
    "price_match": "We offer price matching on identical items from major retailers. Price match requests must be made within 14 days of purchase and require proof of the competitor's current price.",
    "bulk_orders": "Discounts are available for bulk orders of 10+ items. Contact our sales team for a custom quote. Corporate accounts receive additional benefits and dedicated support.",
    "membership": "Our premium membership costs $49/year and includes free shipping on all orders, exclusive discounts, early access to sales, and extended return periods of 60 days.",
}

# Expanded product catalog with more details
PRODUCTS = [
    {"id": "p001", "name": "Wireless Earbuds", "price": 49.99, "category": "Audio", "rating": 4.5, "stock": 120},
    {"id": "p002", "name": "Smart Watch", "price": 129.99, "category": "Wearables", "rating": 4.3, "stock": 85},
    {"id": "p003", "name": "Bluetooth Speaker", "price": 39.99, "category": "Audio", "rating": 4.7, "stock": 200},
    {"id": "p004", "name": "Portable Charger", "price": 19.99, "category": "Accessories", "rating": 4.4, "stock": 300},
    {"id": "p005", "name": "Fitness Tracker", "price": 59.99, "category": "Wearables", "rating": 4.1, "stock": 75},
    {"id": "p006", "name": "Wireless Headphones", "price": 89.99, "category": "Audio", "rating": 4.6, "stock": 95},
    {"id": "p007", "name": "Smart Home Hub", "price": 129.99, "category": "Smart Home", "rating": 4.2, "stock": 60},
    {"id": "p008", "name": "Tablet", "price": 199.99, "category": "Computing", "rating": 4.5, "stock": 40},
    {"id": "p009", "name": "Wireless Keyboard", "price": 49.99, "category": "Computing", "rating": 4.3, "stock": 110},
    {"id": "p010", "name": "Smartphone", "price": 499.99, "category": "Mobile", "rating": 4.8, "stock": 25},
]

# Convert products list to a dictionary for easier access
PRODUCT_DICT = {p["id"]: p for p in PRODUCTS}

# Enhanced order statuses with descriptions
ORDER_STATUSES = [
    {"code": "processing", "label": "Processing", "description": "Your order has been received and is being processed."},
    {"code": "payment_confirmed", "label": "Payment Confirmed", "description": "Your payment has been confirmed and we're preparing your items."},
    {"code": "shipped", "label": "Shipped", "description": "Your order has been shipped and is on its way to you."},
    {"code": "out_for_delivery", "label": "Out for Delivery", "description": "Your order is out for delivery and should arrive today."},
    {"code": "delivered", "label": "Delivered", "description": "Your order has been delivered successfully."},
    {"code": "delayed", "label": "Delayed", "description": "Your order has been delayed. We apologize for the inconvenience."},
    {"code": "cancelled", "label": "Cancelled", "description": "Your order has been cancelled as requested."},
    {"code": "returned", "label": "Returned", "description": "Your return has been processed successfully."},
]

# Detailed product catalog with descriptions, features, and compatibility
MOCK_PRODUCT_CATALOG = {
    "earbuds": {
        "name": "Wireless Earbuds",
        "price": 49.99,
        "description": "High quality sound with deep bass and crystal clear treble. Features active noise cancellation and transparency mode.",
        "features": ["8-hour battery life", "IPX5 water resistance", "Touch controls", "Voice assistant support"],
        "compatibility": ["iOS", "Android", "Windows", "macOS"],
        "colors": ["Black", "White", "Blue"],
        "warranty": "1 year"
    },
    "watch": {
        "name": "Smart Watch",
        "price": 129.99,
        "description": "Track your fitness goals, receive notifications, and monitor your health with our advanced smart watch.",
        "features": ["Heart rate monitor", "Sleep tracking", "GPS", "50+ workout modes", "7-day battery life"],
        "compatibility": ["iOS 12+", "Android 8.0+"],
        "colors": ["Black", "Silver", "Rose Gold"],
        "warranty": "2 years"
    },
    "speaker": {
        "name": "Bluetooth Speaker",
        "price": 39.99,
        "description": "Portable and waterproof speaker with powerful 360° sound for indoor and outdoor use.",
        "features": ["12-hour battery life", "IPX7 waterproof", "Bluetooth 5.0", "Built-in microphone"],
        "compatibility": ["Any Bluetooth device"],
        "colors": ["Black", "Blue", "Red"],
        "warranty": "1 year"
    },
    "charger": {
        "name": "Portable Charger",
        "price": 19.99,
        "description": "Fast charging 10,000mAh power bank with USB-C and USB-A ports for multiple device compatibility.",
        "features": ["10,000mAh capacity", "18W fast charging", "Dual USB ports", "LED power indicator"],
        "compatibility": ["Smartphones", "Tablets", "Wireless earbuds", "Other USB devices"],
        "colors": ["Black", "White"],
        "warranty": "18 months"
    },
    "tracker": {
        "name": "Fitness Tracker",
        "price": 59.99,
        "description": "Slim and lightweight fitness band with heart rate and sleep monitoring for health-conscious users.",
        "features": ["Heart rate monitoring", "Sleep tracking", "14+ exercise modes", "5-day battery life", "Water resistant"],
        "compatibility": ["iOS 11+", "Android 7.0+"],
        "colors": ["Black", "Blue", "Pink"],
        "warranty": "1 year"
    }
}

def get_session_id(session_id: str = Cookie(None)):
    """Manages or creates a session ID."""
    if not session_id or session_id == "null": # Handle JS null cookie value
        session_id = str(uuid4())
    print(f"Using session ID: {session_id}")
    return session_id

def load_history(session_id: str) -> List[BaseMessage]:
    """Loads history from store and converts to LangChain messages."""
    history_dicts = langraph_session_store.get(session_id, [])
    messages = []
    for msg_dict in history_dicts:
        if msg_dict.get("type") == "human":
            messages.append(HumanMessage(content=msg_dict.get("content", "")))
        elif msg_dict.get("type") == "ai":
            messages.append(AIMessage(content=msg_dict.get("content", "")))
    return messages

def save_history(session_id: str, messages: List[BaseMessage]):
    """Converts LangChain messages to dicts and saves to store."""
    langraph_session_store[session_id] = [
        {"type": msg.type, "content": msg.content} for msg in messages
    ]

class BotMessageRequest(BaseModel):
    message: str
    session_data: Optional[Dict[str, Any]] = None

class QuickAction(BaseModel):
    label: str
    value: str
    icon: Optional[str] = None

class ProductInfo(BaseModel):
    id: str
    name: str
    price: float
    image_url: Optional[str] = None
    description: Optional[str] = None

class OrderInfo(BaseModel):
    order_id: str
    status: str
    status_description: Optional[str] = None
    tracking_number: Optional[str] = None
    estimated_delivery: Optional[str] = None

class BotMessageResponse(BaseModel):
    reply: str
    quick_actions: Optional[List[QuickAction]] = None
    products: Optional[List[ProductInfo]] = None
    order_info: Optional[OrderInfo] = None
    confidence_score: Optional[float] = None
    source: Optional[str] = None
    thinking_process: Optional[List[Dict[str, Any]]] = None

from app.services.bot_service import BotService

# Initialize bot service
bot_service = BotService()

@router.post("/bot", response_model=BotMessageResponse)
async def bot_message(
    request: BotMessageRequest,
    response: Response,
    session_id: str = Cookie(None),
    db: Session = Depends(get_db)
):
    """Process a message sent to the bot and return a response"""
    
    # Ensure we have a session ID
    if not session_id:
        session_id = str(uuid4())
        response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="Lax", max_age=3600*24*7) # 1 week
    
    # Get or initialize session state
    if session_id not in session_states:
        session_states[session_id] = {
            "history": [],
            "context": {}
        }
    
    # Add user message to history
    session_states[session_id]["history"].append({
        "role": "user",
        "content": request.message
    })
    
    # Process message
    user_message = request.message.lower()
    
    # Get bot settings from database
    bot_settings_model = get_bot_settings_model(db)
    
    # Simple intent detection
    intent = "general"
    if any(word in user_message for word in ["shipping", "delivery", "arrive"]):
        intent = "shipping"
    elif any(word in user_message for word in ["return", "refund", "money back"]):
        intent = "return"
    elif any(word in user_message for word in ["pay", "payment", "credit card", "debit"]):
        intent = "payment"
    elif any(word in user_message for word in ["warranty", "guarantee", "broken", "repair"]):
        intent = "warranty"
    elif any(word in user_message for word in ["price match", "cheaper", "discount", "coupon"]):
        intent = "price_match"
    elif any(word in user_message for word in ["bulk", "wholesale", "large order", "corporate"]):
        intent = "bulk_orders"
    elif any(word in user_message for word in ["membership", "premium", "subscribe", "subscription"]):
        intent = "membership"
    elif any(word in user_message for word in ["order", "status", "tracking"]):
        intent = "order_status"
    elif any(word in user_message for word in ["product", "item", "buy", "purchase"]):
        intent = "product_info"
    
    # Generate response based on intent
    reply = ""
    quick_actions = []
    products = None
    order_info = None
    
    if intent in FAQS:
        reply = FAQS[intent]
    elif intent == "order_status":
        # Mock order status
        order_id = "ORD" + str(random.randint(10000, 99999))
        status = random.choice(["processing", "shipped", "delivered", "cancelled"])
        status_obj = next((s for s in ORDER_STATUSES if s["code"] == status), None)
        
        order_date = (datetime.now() - timedelta(days=random.randint(1, 10))).strftime("%B %d, %Y")
        estimated_delivery = (datetime.now() + timedelta(days=random.randint(1, 5))).strftime("%B %d, %Y")
        
        reply = f"I found your order {order_id}. It is currently {status_obj['label']}. {status_obj['description']}"
        
        if status == "shipped":
            reply += f" Your package should arrive by {estimated_delivery}."
        
        order_info = OrderInfo(
            order_id=order_id,
            status=status_obj["label"],
            status_description=status_obj["description"],
            tracking_number="TRK" + str(random.randint(10000, 99999)),
            estimated_delivery=estimated_delivery if status == "shipped" else None
        )
    elif intent == "product_info":
        # Extract product type from message
        product_type = None
        for key in MOCK_PRODUCT_CATALOG.keys():
            if key in user_message:
                product_type = key
                break
        
        if product_type:
            product = MOCK_PRODUCT_CATALOG[product_type]
            reply = f"Here's information about our {product['name']}: {product['description']} It's priced at ${product['price']}."
            
            # Add related products
            products = []
            for p in PRODUCTS[:3]:  # Just show first 3 products
                products.append(ProductInfo(
                    id=p["id"],
                    name=p["name"],
                    price=p["price"],
                    description=f"Our popular {p['name']} with {p['rating']} star rating"
                ))
        else:
            reply = "We have a wide range of products. Here are some of our popular items:"
            products = []
            for p in PRODUCTS[:5]:  # Show first 5 products
                products.append(ProductInfo(
                    id=p["id"],
                    name=p["name"],
                    price=p["price"],
                    description=f"Our popular {p['name']} with {p['rating']} star rating"
                ))
    else:
        # Default response using database settings
        reply = bot_settings_model.fallback_message
    
    # Add bot message to history
    session_states[session_id]["history"].append({
        "role": "assistant",
        "content": reply
    })
    
    # Add quick actions from database settings
    if bot_settings_model.quick_actions:
        quick_actions = [QuickAction(**qa) for qa in bot_settings_model.quick_actions]
    
    return BotMessageResponse(
        reply=reply,
        quick_actions=quick_actions,
        products=products,
        order_info=order_info
    )

@router.post("/v2/bot/message", response_model=BotMessageResponse)
async def langgraph_bot_message(
    request: BotMessageRequest,
    response: Response,
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db),
    debug: bool = Query(False)
):
    """Handles bot messages using the LangGraph workflow."""
    print(f"\n--- New Request --- Session: {session_id}, Message: {request.message}")
    user_message = request.message

    # 1. Load conversation history
    history = load_history(session_id)
    print(f"--- Loaded History ({len(history)} messages) ---")

    # 2. Prepare initial state for the graph
    initial_state: ConversationState = {
        "messages": history,
        "user_message": user_message,
        "intent": None,
        "retrieved_context": None,
        "action_result": None,
    }

    # 3. Invoke the graph
    final_state = None
    thinking_process = []
    
    # Create a simpler approach to capture the thinking process
    thinking_steps = []
    
    # Define a function to capture stdout
    def capture_stdout(message):
        thinking_steps.append({"type": "stdout", "content": message})
        print(message)  # Also print to the real stdout
    
    # Monkey patch the print function in specific modules to capture thinking
    original_print = print
    
    try:
        print("--- Invoking Graph ---")
        # Set up a custom print function to capture thinking process if debug is enabled
        if debug:
            def custom_print(*args, **kwargs):
                message = ' '.join(str(arg) for arg in args)
                thinking_steps.append({"type": "stdout", "content": message})
                original_print(*args, **kwargs)
            
            # Patch the print function in relevant modules
            import builtins
            builtins.print = custom_print
            
            # Add a thinking step to mark the start of processing
            thinking_steps.append({"type": "text", "content": f"Processing message: {user_message}"})
            
        # Execute the graph
        final_state = await graph_app.ainvoke(initial_state)
        
        # Restore original print function if debug was enabled
        if debug:
            import builtins
            builtins.print = original_print
            
            # Add thinking steps to the process
            thinking_process.extend(thinking_steps)
            
        print("--- Graph Invocation Complete ---")

    except Exception as e:
        print(f"--- Graph Error: {e} ---")
        # Handle graph execution error
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing message: {e}")

    if not final_state or not final_state.get("messages"):
        raise HTTPException(status_code=500, detail="Graph did not return expected state.")

    # 4. Extract the final response
    final_messages = final_state["messages"]
    ai_reply = final_messages[-1].content if final_messages and isinstance(final_messages[-1], AIMessage) else "Sorry, I couldn't generate a response."

    # 5. Save updated history
    save_history(session_id, final_messages)
    print(f"--- Saved History ({len(final_messages)} messages) ---")

    # 6. Set session cookie
    response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="Lax", max_age=3600*24*7) # 1 week

    # 7. Prepare quick actions based on intent
    intent = final_state.get("intent")
    quick_actions = None
    if intent == "order_status":
        quick_actions = [
            QuickAction(label="Track Package", value="Track my package"),
            QuickAction(label="Cancel Order", value="I want to cancel my order")
        ]
    elif intent == "knowledge_base_query":
        quick_actions = [
            QuickAction(label="Return Policy", value="What's your return policy?"),
            QuickAction(label="Shipping Info", value="How long does shipping take?")
        ]
    elif intent == "product_availability":
        quick_actions = [
            QuickAction(label="Check Another Product", value="Is the smart watch in stock?"),
            QuickAction(label="Compare Products", value="Compare wireless earbuds and headphones")
        ]

    # 8. Extract any product or order information from action_result
    products = None
    order_info = None
    action_result = final_state.get("action_result")
    
    if action_result and "product_availability" in action_result:
        product_data = action_result["product_availability"]
        if isinstance(product_data, dict) and "product_name" in product_data:
            products = [
                ProductInfo(
                    id=str(random.randint(1000, 9999)),  # Mock ID
                    name=product_data["product_name"],
                    price=next((p["price"] for p in PRODUCTS if p["name"] == product_data["product_name"]), 99.99),
                    description=f"Availability: {product_data.get('availability', 'Unknown')}",
                    image_url=f"https://ui-avatars.com/api/?name={product_data['product_name']}&size=128"
                )
            ]
    
    if action_result and "order_status" in action_result:
        order_data = action_result["order_status"]
        if isinstance(order_data, dict) and "order_id" in order_data:
            order_info = OrderInfo(
                order_id=order_data["order_id"],
                status=order_data.get("status", "Unknown"),
                status_description=f"Order placed on {order_data.get('order_date', 'unknown date')}",
                tracking_number=f"TRK{random.randint(10000, 99999)}",
                estimated_delivery=order_data.get("estimated_delivery")
            )

    # 9. Return response
    return BotMessageResponse(
        reply=ai_reply,
        quick_actions=quick_actions,
        products=products,
        order_info=order_info,
        confidence_score=0.95,  # Mock confidence score
        source="langgraph",
        thinking_process=thinking_process if debug else None
    )

@router.post("/v2/bot/test-knowledge", response_model=BotMessageResponse)
async def test_knowledge_bot_message(
    request: BotMessageRequest,
    response: Response,
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db)
):
    """Test endpoint that directly uses the vector store for knowledge retrieval."""
    print(f"\n--- New Test Request --- Session: {session_id}, Message: {request.message}")
    user_message = request.message

    # 1. Load conversation history
    history = load_history(session_id)
    print(f"--- Loaded History ({len(history)} messages) ---")
    
    # 2. Get bot settings from database
    bot_settings = get_bot_settings_model(db)
    
    # 3. Determine intent and retrieve context
    intent = "general"
    retrieved_context = None
    action_result = None
    rag_service = RAGService()
    search_results = rag_service.search_similar(user_message, top_k=2)
    
    retrieved_context = None
    intent = "knowledge_base_query"
    
    # Extract text from search results
    texts = []
    if search_results:
        for result in search_results:
            if isinstance(result, dict) and "text" in result:
                texts.append(result["text"])
                print(f"--- Found text result: {result['text'][:100]}... ---")
    
    # Combine texts into a single context
    if texts:
        retrieved_context = "\n\n".join(texts)
        print(f"--- Retrieved context of length {len(retrieved_context)} ---")

    # 3. Prepare initial state for the graph
    initial_state: ConversationState = {
        "messages": history,
        "user_message": user_message,
        "intent": intent,
        "retrieved_context": retrieved_context,
        "action_result": None,
    }

    # 4. Invoke the graph
    final_state = None
    try:
        print("--- Invoking Graph ---")
        final_state = await graph_app.ainvoke(initial_state)
        print("--- Graph Invocation Complete ---")

    except Exception as e:
        print(f"--- Graph Error: {e} ---")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing message: {e}")

    if not final_state or not final_state.get("messages"):
        raise HTTPException(status_code=500, detail="Graph did not return expected state.")

    # 5. Extract the final response
    final_messages = final_state["messages"]
    ai_reply = final_messages[-1].content if final_messages and isinstance(final_messages[-1], AIMessage) else "Sorry, I couldn't generate a response."

    # 6. Save updated history
    save_history(session_id, final_messages)
    print(f"--- Saved History ({len(final_messages)} messages) ---")

    # 7. Set session cookie
    response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="Lax", max_age=3600*24*7) # 1 week

    # 8. Get bot settings from database
    bot_settings = get_bot_settings_model(db)
    
    # 9. Use quick actions from database settings
    if bot_settings.quick_actions:
        quick_actions = [QuickAction(**qa) for qa in bot_settings.quick_actions]
    else:
        # Fallback to default quick actions
        quick_actions = [
            QuickAction(label="Return Policy", value="What's your return policy?"),
            QuickAction(label="Shipping Info", value="How long does shipping take?")
        ]

    return BotMessageResponse(
        reply=ai_reply,
        quick_actions=quick_actions,
        products=None,
        order_info=None,
        confidence_score=0.95,  # Mock confidence score
        source="langgraph-test"
    )