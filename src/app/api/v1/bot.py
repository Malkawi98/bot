from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Response, Cookie, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.bot import BotMessageRequest, BotMessageResponse, QuickAction, ProductInfo, OrderInfo
from app.schemas.coupon_request import CouponRequestModel, CouponResponseModel
from app.services.bot_service import BotService
from app.services.coupon_service import CouponService
from app.services.rag import RAGService
from app.services.graph_service.state import ConversationState
from app.services.graph_service.graph import graph_app
from app.services.graph_service.history import load_history, save_history
from app.services.graph_service.llm import llm
from langchain_core.messages import HumanMessage, AIMessage
import random
import json
import uuid
import sys
import io
import re
from typing import List, Dict, Any, Optional

router = APIRouter(tags=["bot"])

# Import templates from the centralized configuration
from app.core.template_config import templates

# Initialize RAG service
rag_service = RAGService()

# In-memory session state (for demo only)
session_states = {}

# Session store moved to app.services.graph_service.history

# In-memory product catalog (for demo only)
product_catalog = {}

# Import constants from the centralized file
from app.core.bot_constants import FAQS, PRODUCTS, ORDER_STATUSES

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
        session_id = str(uuid.uuid4())
    print(f"Using session ID: {session_id}")
    return session_id

# History functions moved to app.services.graph_service.history

# Models moved to app.schemas.bot

def generate_coupon_prompt(coupon_data: dict, language: str = "en") -> str:
    """Generate a prompt for the AI to respond about a specific coupon."""
    if language == "ar":
        # Arabic prompt
        return f"""أنت مساعد دعم متجر إلكتروني مفيد. قم بإخبار العميل عن الكوبون التالي بطريقة ودية ومفيدة:

معلومات الكوبون:
الرمز: {coupon_data['code']}
الخصم: {coupon_data['discount']}%
الوصف: {coupon_data['description'] if coupon_data['description'] else 'لا يوجد وصف'}
تاريخ الانتهاء: {coupon_data['expires_at'] if coupon_data['expires_at'] else 'لا تاريخ انتهاء'}
نشط: {'نعم' if coupon_data['is_active'] else 'لا'}

قدم إجابة مختصرة وودية تتضمن جميع المعلومات المهمة عن الكوبون. لا تذكر أنك مساعد ذكاء اصطناعي."""
    else:
        # English prompt (default)
        return f"""You are a helpful e-commerce support assistant. Tell the customer about the following coupon in a friendly and helpful way:

Coupon Information:
Code: {coupon_data['code']}
Discount: {coupon_data['discount']}%
Description: {coupon_data['description'] if coupon_data['description'] else 'No description provided'}
Expiration Date: {coupon_data['expires_at'] if coupon_data['expires_at'] else 'No expiration date'}
Active: {'Yes' if coupon_data['is_active'] else 'No'}

Provide a concise and friendly response that includes all the important information about the coupon. Do not mention that you are an AI assistant."""

def generate_coupons_list_prompt(coupons_data: dict, language: str = "en") -> str:
    """Generate a prompt for the AI to respond with a list of available coupons."""
    coupons = coupons_data["coupons"]
    count = coupons_data["count"]
    has_coupons = coupons_data["has_coupons"]
    
    if not has_coupons:
        if language == "ar":
            return "أنت مساعد دعم متجر إلكتروني مفيد. أخبر العميل بطريقة لطيفة أنه لا توجد كوبونات نشطة متاحة حاليًا."
        else:
            return "You are a helpful e-commerce support assistant. Politely inform the customer that there are no active coupons available at the moment."
    
    # Format coupon details for the prompt
    coupon_details = ""
    for i, coupon in enumerate(coupons, 1):
        expiry = coupon["expires_at"] if coupon["expires_at"] else "No expiration date"
        desc = coupon["description"] if coupon["description"] else ""
        
        if language == "ar":
            coupon_details += f"{i}. الرمز: {coupon['code']}, الخصم: {coupon['discount']}%, {desc}, تاريخ الانتهاء: {expiry}\n"
        else:
            coupon_details += f"{i}. Code: {coupon['code']}, Discount: {coupon['discount']}%, {desc}, Expires: {expiry}\n"
    
    if language == "ar":
        return f"""أنت مساعد دعم متجر إلكتروني مفيد. قم بإخبار العميل عن الكوبونات النشطة المتاحة حاليًا بطريقة ودية ومفيدة. هناك {count} كوبون(ات) نشط(ة):

{coupon_details}
قدم إجابة مختصرة وودية تتضمن جميع الكوبونات المتاحة وكيفية استخدامها. لا تذكر أنك مساعد ذكاء اصطناعي."""
    else:
        return f"""You are a helpful e-commerce support assistant. Tell the customer about the currently available active coupons in a friendly and helpful way. There are {count} active coupon(s):

{coupon_details}
Provide a concise and friendly response that lists all the available coupons and how to use them. Do not mention that you are an AI assistant."""


from app.services.bot_service import BotService

@router.post("/request-coupon", response_model=CouponResponseModel)
async def request_coupon(
    request: CouponRequestModel,
    response: Response,
    session_id: str = Depends(get_session_id),
    db: Session = Depends(get_db)
):
    """Request a specific coupon code. Users can only request one coupon per session."""
    coupon_service = CouponService(db)
    language = request.language or "en"
    
    # Request the coupon
    result = coupon_service.request_coupon(session_id, request.coupon_code.upper())
    
    # Set cookie to maintain session
    response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="Lax", max_age=3600*24*7)
    
    # Generate appropriate message based on result
    message = ""
    if result["message"] == "already_assigned":
        # User already has a coupon
        coupon = result["coupon"]
        if language == "ar":
            message = f"لقد حصلت بالفعل على كوبون {result['assigned_code']}. لا يمكنك طلب كوبون آخر في هذه الجلسة."
        else:
            message = f"You have already received coupon {result['assigned_code']}. You cannot request another coupon in this session."
    elif result["message"] == "invalid_coupon":
        # Requested coupon is invalid
        if language == "ar":
            message = f"عذراً، الكوبون {request.coupon_code} غير صالح أو غير متوفر. يرجى التحقق من الرمز والمحاولة مرة أخرى."
        else:
            message = f"Sorry, the coupon {request.coupon_code} is invalid or unavailable. Please check the code and try again."
    else:
        # Success
        coupon = result["coupon"]
        if language == "ar":
            message = f"تم تخصيص الكوبون {result['assigned_code']} لك بنجاح! استمتع بخصم {coupon['discount']}%."
        else:
            message = f"Coupon {result['assigned_code']} has been successfully assigned to you! Enjoy {coupon['discount']}% off."
    
    # Prepare response
    response_data = CouponResponseModel(
        success=result["success"],
        message=message,
        already_assigned=result["already_assigned"],
        assigned_code=result["assigned_code"]
    )
    
    # Add coupon details if available
    if result["coupon"]:
        coupon = result["coupon"]
        response_data.coupon_code = coupon["code"]
        response_data.discount = coupon["discount"]
        response_data.description = coupon["description"]
        response_data.expires_at = coupon["expires_at"]
    
    return response_data

@router.post("/message", response_model=BotMessageResponse)
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
    
    # Initialize bot service with database session
    bot_service = BotService(db)
    
    # Process the message using the bot service
    reply, quick_actions, additional_data, confidence = bot_service.process_message(user_message, session_states[session_id])
    
    # Add bot message to history
    session_states[session_id]["history"].append({
        "role": "assistant",
        "content": reply
    })
    
    # Add quick actions from database settings
    if bot_settings_model.quick_actions:
        quick_actions = [QuickAction(**qa) for qa in bot_settings_model.quick_actions]
    
    # Extract products and order info from additional_data if available
    products = None
    order_info = None
    coupons = None
    coupon = None
    if additional_data:
        if 'products' in additional_data:
            products = additional_data['products']
        if 'order_info' in additional_data:
            order_info = additional_data['order_info']
        if 'coupons' in additional_data:
            coupons = additional_data['coupons']
        if 'coupon' in additional_data:
            coupon = additional_data['coupon']
    
    return BotMessageResponse(
        reply=reply,
        quick_actions=quick_actions,
        products=products,
        order_info=order_info,
        coupons=coupons,
        coupon=coupon,
        confidence_score=confidence
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

    # Check if this is a coupon-related query
    # Include both English and Arabic keywords for coupon detection
    coupon_patterns = [
        # English patterns
        r'coupon', r'discount', r'promo code', r'promotion', r'offer', r'deal',
        # Arabic patterns
        r'كوبون', r'خصم', r'تخفيض', r'رمز ترويجي', r'عرض', r'صفقة'
    ]
    
    is_coupon_query = any(re.search(pattern, user_message.lower()) for pattern in coupon_patterns)
    
    # Check if this is a product-related query in Arabic
    is_product_query = False
    specific_product_query = False
    product_name = None
    
    if request.language == 'ar':
        # Match common Arabic patterns for general product queries
        is_product_query = re.search(r'\u0645\u0646\u062a\u062c\u0627\u062a|\u0628\u0636\u0627\u0626\u0639|\u0633\u0644\u0639', user_message) is not None
        
        # Check for specific product queries in Arabic
        # Pattern for "هل لديكم [product]?" or "هل عندكم [product]?"
        specific_match = re.search(r'\u0647\u0644 \u0644\u062f\u064a\u0643\u0645 ([\u0600-\u06FF\s]+)|\u0647\u0644 \u0639\u0646\u062f\u0643\u0645 ([\u0600-\u06FF\s]+)', user_message)
        if specific_match:
            specific_product_query = True
            product_name = specific_match.group(1) if specific_match.group(1) else specific_match.group(2)
            # Remove question mark if present
            product_name = product_name.strip().rstrip('؟').strip()
            print(f"--- Detected specific Arabic product query for: {product_name} ---")
        # Handle specific product query in Arabic
        if specific_product_query and product_name:
            print(f"--- Processing specific Arabic product query for: {product_name} ---")
            from app.services.product_search import ProductSearchService
            product_search = ProductSearchService(db)
            found, product_info = product_search.search_product_by_name(product_name, language='ar')
            
            if found:
                # Generate Arabic response for specific product
                response_text = f"نعم، {product_info['name']} متوفر لدينا! "
                if product_info['stock'] > 0:
                    response_text += f"يوجد حالياً {product_info['stock']} قطعة بسعر {product_info['price']} {product_info['currency']}."
                else:
                    response_text += "للأسف نفذت الكمية حالياً."
                
                if product_info.get('description'):
                    response_text += f" {product_info['description']}"
                
                # Add to history
                history.append(HumanMessage(content=user_message))
                history.append(AIMessage(content=response_text))
                save_history(session_id, history)
                
                # Set cookie
                response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="Lax", max_age=3600*24*7)
                
                # Check if this is the first message in the conversation
                # Print history length for debugging
                print(f"--- History length: {len(history)} for session {session_id} ---")
                is_first_message = len(history) <= 1  # Only the system message or empty history
                
                # Only include quick actions for the first message
                quick_actions = None
                if is_first_message:
                    quick_actions = [
                        QuickAction(label="منتج آخر", value="هل لديكم ساعة ذكية؟"),
                        QuickAction(label="مقارنة المنتجات", value="قارن بين السماعات اللاسلكية وسماعات الرأس")
                    ]
                
                return BotMessageResponse(
                    reply=response_text,
                    products=[{
                        "id": str(product_info['id']),
                        "name": product_info['name'],
                        "price": product_info['price'],
                        "description": product_info.get('description', '')
                    }],
                    quick_actions=quick_actions,
                    confidence_score=0.95,
                    source="direct_arabic_product_search"
                )
            else:
                # Product not found response
                response_text = f"عذراً، لا يتوفر لدينا {product_name} حالياً. هل تود الاستفسار عن منتج آخر؟"
                
                # Add to history
                history.append(HumanMessage(content=user_message))
                history.append(AIMessage(content=response_text))
                save_history(session_id, history)
                
                # Set cookie
                response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="Lax", max_age=3600*24*7)
                
                # No quick actions for product not found responses
                return BotMessageResponse(
                    reply=response_text,
                    confidence_score=0.95,
                    source="direct_arabic_product_search"
                )
        
        # Handle general product query in Arabic
        elif is_product_query:
            print(f"--- Detected general Arabic product query: {user_message} ---")
            # Get products directly
            from app.services.product import ProductService
            product_service = ProductService(db)
            products = product_service.get_products(limit=10)
            
            if products and len(products) > 0:
                # Format products for response
                product_list = []
                for p in products:
                    product_list.append({
                        "id": str(p.id),  # Convert ID to string to match the expected type
                        "name": p.name,
                        "price": p.price,
                        "currency": p.currency,
                        "stock": p.stock_quantity,
                        "category": p.category,
                        "description": p.description or ""
                    })
                
                # Generate Arabic response
                response_text = "وجدت المنتجات التالية في مخزوننا:\n\n"
                for i, product in enumerate(product_list, 1):
                    response_text += f"{i}. {product['name']} - {product['price']} {product['currency']} - "
                    response_text += "متوفر" if product['stock'] > 0 else "غير متوفر"
                    if product['description']:
                        response_text += f" - {product['description']}"
                    response_text += "\n"
                
                response_text += "\nهل ترغب في معرفة المزيد عن أي من هذه المنتجات؟"
                
                # Add to history
                history.append(HumanMessage(content=user_message))
                history.append(AIMessage(content=response_text))
                save_history(session_id, history)
                
                # Set cookie
                response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="Lax", max_age=3600*24*7)
                
                # Check if this is the first message in the conversation
                # Print history length for debugging
                print(f"--- History length: {len(history)} for session {session_id} ---")
                is_first_message = len(history) <= 1  # Only the system message or empty history
                
                # Only include quick actions for the first message
                quick_actions = None
                if is_first_message:
                    quick_actions = [
                        QuickAction(label="منتج آخر", value="هل لديكم ساعة ذكية؟"),
                        QuickAction(label="مقارنة المنتجات", value="قارن بين السماعات اللاسلكية وسماعات الرأس")
                    ]
                
                return BotMessageResponse(
                    reply=response_text,
                    products=product_list,
                    quick_actions=quick_actions,
                    confidence_score=0.95,
                    source="direct_arabic_product_search"
                )
    
    # If it's a coupon query, handle it directly here
    if is_coupon_query:
        coupon_service = CouponService(db)
        language = request.language or "en"
        
        # First, check if the user has already received a coupon in this session
        if coupon_service.has_received_coupon(session_id):
            assigned_code = coupon_service.get_assigned_coupon(session_id)
            assigned_coupon = coupon_service.get_coupon_by_code(assigned_code)
            
            if assigned_coupon:
                # User already has a coupon - inform them they can't get another one
                formatted_coupon = coupon_service.format_coupon_for_display(assigned_coupon)
                
                if language == "ar":
                    ai_response = f"لقد حصلت بالفعل على كوبون {assigned_code}. لا يمكنك طلب كوبون آخر في هذه الجلسة. يمكنك استخدام هذا الكوبون للحصول على خصم {formatted_coupon['discount']}%."
                else:
                    ai_response = f"You have already received coupon {assigned_code}. You cannot request another coupon in this session. You can use this coupon to get {formatted_coupon['discount']}% off your purchase."
                
                # Add to history
                history.append(HumanMessage(content=user_message))
                history.append(AIMessage(content=ai_response))
                save_history(session_id, history)
                
                # Set cookie
                response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="Lax", max_age=3600*24*7)
                
                return BotMessageResponse(
                    reply=ai_response,
                    coupon=formatted_coupon,
                    confidence_score=0.95,
                    source="coupon_service"
                )
        
        # Check if asking for a specific coupon code (support both English and Arabic)
        code_match = None
        
        # English pattern
        english_match = re.search(r'coupon\s+(?:code\s+)?([A-Za-z0-9]+)', user_message, re.IGNORECASE)
        if english_match:
            code_match = english_match
        
        # Arabic pattern - matches "كوبون X" or "رمز الخصم X" or similar patterns
        arabic_match = re.search(r'(?:\u0643\u0648\u0628\u0648\u0646|\u0631\u0645\u0632|\u062e\u0635\u0645)\s+([A-Za-z0-9]+)', user_message, re.IGNORECASE)
        if arabic_match:
            code_match = arabic_match
        
        if code_match:
            # Looking for a specific coupon
            code = code_match.group(1).upper()
            
            # Use the request_coupon method to handle the coupon request
            result = coupon_service.request_coupon(session_id, code)
            
            if result["success"]:
                # Coupon successfully assigned
                coupon_data = result["coupon"]
                
                # Generate AI response based on the coupon data
                if language == "ar":
                    ai_response = f"تم تخصيص الكوبون {result['assigned_code']} لك بنجاح! استمتع بخصم {coupon_data['discount']}% على مشترياتك."
                else:
                    ai_response = f"Great! I've assigned coupon {result['assigned_code']} to you. You can use it to get {coupon_data['discount']}% off your purchase."
                
                # Add to history
                history.append(HumanMessage(content=user_message))
                history.append(AIMessage(content=ai_response))
                save_history(session_id, history)
                
                # Set cookie
                response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="Lax", max_age=3600*24*7)
                
                return BotMessageResponse(
                    reply=ai_response,
                    coupon=coupon_data,
                    confidence_score=0.95,
                    source="coupon_service"
                )
            elif result["message"] == "already_assigned":
                # User already has a different coupon
                coupon_data = result["coupon"]
                
                if language == "ar":
                    ai_response = f"لقد حصلت بالفعل على كوبون {result['assigned_code']}. لا يمكنك طلب كوبون آخر في هذه الجلسة."
                else:
                    ai_response = f"You have already received coupon {result['assigned_code']}. You cannot request another coupon in this session."
                
                # Add to history
                history.append(HumanMessage(content=user_message))
                history.append(AIMessage(content=ai_response))
                save_history(session_id, history)
                
                # Set cookie
                response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="Lax", max_age=3600*24*7)
                
                return BotMessageResponse(
                    reply=ai_response,
                    coupon=coupon_data,
                    confidence_score=0.95,
                    source="coupon_service"
                )
            else:
                # Coupon not found or invalid
                if language == "ar":
                    ai_response = f"عذراً، الكوبون {code} غير صالح أو غير متوفر. يرجى التحقق من الرمز والمحاولة مرة أخرى، أو اسأل عن الكوبونات المتاحة."
                else:
                    ai_response = f"Sorry, the coupon {code} is invalid or unavailable. Please check the code and try again, or ask about our available coupons."
                
                # Add to history
                history.append(HumanMessage(content=user_message))
                history.append(AIMessage(content=ai_response))
                save_history(session_id, history)
                
                # Set cookie
                response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="Lax", max_age=3600*24*7)
                
                return BotMessageResponse(
                    reply=ai_response,
                    confidence_score=0.95,
                    source="coupon_service"
                )
        else:
            # Looking for all available coupons - show the list but remind them to choose one
            active_coupons = coupon_service.get_active_coupons()
            
            # Format coupon data for the AI
            coupons_data = coupon_service.format_coupons_list(active_coupons)
            formatted_coupons = coupons_data["coupons"]
            
            # Check if user already has a coupon
            has_coupon = coupon_service.has_received_coupon(session_id)
            assigned_code = coupon_service.get_assigned_coupon(session_id) if has_coupon else None
            
            # Generate appropriate prompt based on whether user already has a coupon
            if has_coupon:
                if language == "ar":
                    ai_response = f"لقد حصلت بالفعل على كوبون {assigned_code}. لا يمكنك طلب كوبون آخر في هذه الجلسة."
                else:
                    ai_response = f"You have already received coupon {assigned_code}. You cannot request another coupon in this session."
            else:
                # Generate AI response based on the coupons data
                if language == "ar":
                    # Use the coupon data to generate a dynamic response in Arabic
                    coupon_count = len(formatted_coupons)
                    
                    if coupon_count == 0:
                        ai_response = "عذرًا، لا توجد كوبونات نشطة متاحة في الوقت الحالي. يرجى التحقق مرة أخرى لاحقًا."
                    else:
                        # Generate a dynamic intro based on the number of coupons
                        if coupon_count == 1:
                            ai_response = f"لدينا عرض ترويجي نشط: {formatted_coupons[0]['description'] or 'خصم خاص'}\n\n"
                        else:
                            ai_response = f"لدينا عدة عروض ترويجية متاحة حاليًا:\n\n"
                        
                        # Add each coupon to the response, focusing on description rather than value
                        for coupon in formatted_coupons:
                            expiry = f" (صالح حتى {coupon['expires_at']})" if coupon['expires_at'] else ""
                            
                            # If there's a description, use it but filter out percentage values
                            if coupon['description']:
                                # Remove any percentage references from the description
                                filtered_description = re.sub(r'\d+%|\d+\.\d+%|\d+ ?%', 'خصم', coupon['description'])
                                ai_response += f"• {filtered_description} - استخدم الرمز '{coupon['code']}'{expiry}\n"
                            else:
                                # If no description, just show the code without the discount value
                                ai_response += f"• عرض خاص - استخدم الرمز '{coupon['code']}'{expiry}\n"
                else:
                    # Use the coupon data to generate a dynamic response
                    coupon_count = len(formatted_coupons)
                    
                    if coupon_count == 0:
                        ai_response = "I'm sorry, but there are no active coupons available at the moment. Please check back later."
                    else:
                        # Generate a dynamic intro based on the number of coupons
                        if coupon_count == 1:
                            ai_response = f"We currently have an active promotion: {formatted_coupons[0]['description'] or 'Special discount'}\n\n"
                        else:
                            ai_response = f"We have several promotions currently available:\n\n"
                        
                        # Add each coupon to the response, focusing on description rather than value
                        for coupon in formatted_coupons:
                            expiry = f" (valid until {coupon['expires_at']})" if coupon['expires_at'] else ""
                            
                            # If there's a description, use it but filter out percentage values
                            if coupon['description']:
                                # Remove any percentage references from the description
                                filtered_description = re.sub(r'\d+%|\d+\.\d+%|\d+ ?%', 'discount', coupon['description'])
                                ai_response += f"• {filtered_description} - use code '{coupon['code']}'{expiry}\n"
                            else:
                                # If no description, just show the code without the discount value
                                ai_response += f"• Special promotion - use code '{coupon['code']}'{expiry}\n"
            
            # Add to history
            history.append(HumanMessage(content=user_message))
            history.append(AIMessage(content=ai_response))
            save_history(session_id, history)
            
            # Set cookie
            response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="Lax", max_age=3600*24*7)
            
            return BotMessageResponse(
                reply=ai_response,
                coupons=formatted_coupons,
                confidence_score=0.95,
                source="coupon_service"
            )
    
    # 2. Prepare initial state for the graph for non-coupon queries
    initial_state: ConversationState = {
        "messages": history,
        "user_message": user_message,
        "intent": None,
        "retrieved_context": None,
        "action_result": None,
        "language": request.language or "en",  # Pass the language preference
        "session_id": session_id,  # Add the session_id to the state
        "db": db,  # Add the database session to the state
        "frustration_count": 0,  # Initialize frustration count
        "last_error": None  # Initialize last error
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

    if not final_state:
        raise HTTPException(status_code=500, detail="Graph did not return expected state.")

    # 4. Extract the final response
    # Check if there are messages in the final state
    if final_state.get("messages") and len(final_state["messages"]) > 0:
        # Get the last message which should be the AI response
        last_message = final_state["messages"][-1]
        if isinstance(last_message, AIMessage):
            ai_reply = last_message.content
        else:
            ai_reply = "Sorry, I couldn't generate a response."
    else:
        # Fallback if no messages are found
        ai_reply = final_state.get("response", "Sorry, I couldn't generate a response.")

    # Process the result
    response_text = final_state.get("response", "I'm not sure how to respond to that.")
    products = final_state.get("products", None)
    order_info = final_state.get("order_info", None)  # Get order info if available
    coupon = None  # Default value

    # Update history with the new messages
    updated_messages = final_state.get("messages", history + [HumanMessage(content=user_message), AIMessage(content=response_text)])
    save_history(session_id, updated_messages)
    print(f"--- Saved History ({len(updated_messages)} messages) ---")

    # 6. Set session cookie
    response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="Lax", max_age=3600*24*7) # 1 week

    # ... (rest of the code remains the same)
    # 7. Prepare quick actions based on intent, but only for the first message in a conversation
    intent = final_state.get("intent")
    quick_actions = None
    
    # Check if this is the first message in the conversation
    # Print history length for debugging
    print(f"--- History length: {len(history)} for session {session_id} ---")
    is_first_message = len(history) <= 1  # Only the system message or empty history
    
    if is_first_message:
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
    else:
        # No quick actions for subsequent messages
        quick_actions = None

    # 8. Extract any product, order, or coupon information from action_result
    action_result = final_state.get("action_result")
    
    # Keep the products from earlier processing if present
    if not products:
        products = None
        
    # Handle order status information
    if not order_info and action_result and "order_status" in action_result:
        order_status_result = action_result["order_status"]
        if order_status_result.get("found", False) and "order_info" in order_status_result:
            order_info = order_status_result["order_info"]
    
    coupons = None
    coupon = None
    
    # Import random here to ensure it's available in this scope
    import random
    
    if action_result:
        if "product_availability" in action_result:
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
        elif "order_status" in action_result:
            order_data = action_result["order_status"]
            if isinstance(order_data, dict) and "order_id" in order_data:
                order_info = OrderInfo(
                    order_id=order_data["order_id"],
                    status=order_data.get("status", "Unknown"),
                    status_description=f"Order placed on {order_data.get('order_date', 'unknown date')}",
                    tracking_number=f"TRK{random.randint(10000, 99999)}",
                    estimated_delivery=order_data.get("estimated_delivery")
                )
        elif "coupon_query" in action_result:
            coupon_data = action_result["coupon_query"]
            if isinstance(coupon_data, dict):
                if "coupon" in coupon_data:
                    coupon = coupon_data["coupon"]
                if "coupons" in coupon_data:
                    coupons = coupon_data["coupons"]
                # If there's a message in the coupon data, use it as the reply
                if "message" in coupon_data and coupon_data["message"]:
                    ai_reply = coupon_data["message"]

    # 9. Return response
    if debug:
        return BotMessageResponse(
            reply=ai_reply,
            quick_actions=quick_actions,
            products=products,
            order_info=order_info,
            coupons=coupons,
            coupon=coupon,
            confidence_score=0.95,  # Mock confidence score
            source="langgraph",
            thinking_process=thinking_process
        )
    else:
        return BotMessageResponse(
            reply=ai_reply,
            quick_actions=quick_actions,
            products=products,
            order_info=order_info,
            coupons=coupons,
            coupon=coupon,
            confidence_score=0.95,  # Mock confidence score
            source="langgraph"
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
    
    # 3. Get language preference from request or default to English
    language = request.language or "en"
    print(f"--- Using language: {language} ---")
    
    # 4. Determine intent and retrieve context
    intent = "general"
    retrieved_context = None
    action_result = None
    rag_service = RAGService()
    
    # Check if this is a product-related query
    product_info = None
    product_keywords = ["product", "item", "buy", "purchase", "stock", "available", "price"]
    arabic_product_keywords = ["منتج", "سلعة", "شراء", "متوفر", "سعر", "بضاعة"]
    
    is_product_query = any(keyword in user_message.lower() for keyword in product_keywords)
    if language == "ar":
        is_product_query = is_product_query or any(keyword in user_message for keyword in arabic_product_keywords)
    
    if is_product_query:
        # Initialize product service
        product_service = ProductService(db)
        
        # Extract potential product name from the query
        # This is a simplified approach - in production, use NLP for better entity extraction
        import re
        
        # Try to extract product name based on common patterns
        product_name_patterns = [
            r"(?:do you have|looking for|want to buy|sell|stock of)\s+(?:a|an|the)?\s+([\w\s]+?)(?:\?|$|\s+in stock|\s+available)",
            r"(?:هل لديكم|أبحث عن|أريد شراء|بيع|مخزون من)\s+([\w\s]+?)(?:\?|$|\s+متوفر|\s+في المخزون)"
        ]
        
        extracted_product_name = None
        for pattern in product_name_patterns:
            matches = re.search(pattern, user_message, re.IGNORECASE)
            if matches:
                extracted_product_name = matches.group(1).strip()
                break
        
        # If no pattern match, use a simpler approach to extract nouns
        if not extracted_product_name:
            # Remove common question words and stop words
            stop_words = ["do", "you", "have", "any", "the", "a", "an", "in", "stock", "available", 
                          "هل", "لديكم", "أي", "في", "متوفر", "المخزون"]
            
            # Split the message into words and filter out stop words
            words = user_message.lower().split()
            potential_product_words = [word for word in words if word not in stop_words and len(word) > 2]
            
            if potential_product_words:
                # Use the longest word as a potential product name (simple heuristic)
                extracted_product_name = max(potential_product_words, key=len)
        
        # Get all products matching the language
        products = product_service.get_products(language=language)
        
        # Check if we have the exact product
        exact_product = None
        if extracted_product_name:
            for product in products:
                if extracted_product_name.lower() in product.name.lower():
                    exact_product = product
                    break
        
        if exact_product:
            # We found the exact product the user is looking for
            stock_status = "In stock" if exact_product.stock_quantity > 0 else "Out of stock"
            if language == "ar":
                stock_status = "متوفر" if exact_product.stock_quantity > 0 else "غير متوفر"
                product_info = f"المنتج: {exact_product.name}\nالسعر: {exact_product.price} {exact_product.currency}\nالحالة: {stock_status}\nالوصف: {exact_product.description or 'لا يوجد وصف متاح'}\n"
            else:
                product_info = f"Product: {exact_product.name}\nPrice: {exact_product.price} {exact_product.currency}\nStatus: {stock_status}\nDescription: {exact_product.description or 'No description available'}\n"
        elif extracted_product_name:
            # We didn't find the exact product, but let's suggest similar products
            similar_products = product_service.find_similar_products(extracted_product_name, language=language)
            
            if similar_products:
                # We found similar products to suggest
                if language == "ar":
                    product_info = f"لم نتمكن من العثور على '{extracted_product_name}' بالضبط، ولكن لدينا هذه المنتجات المشابهة:\n\n"
                    for product in similar_products:
                        stock_status = "متوفر" if product.stock_quantity > 0 else "غير متوفر"
                        product_info += f"- {product.name}: {product.price} {product.currency} ({stock_status})\n"
                else:
                    product_info = f"We couldn't find '{extracted_product_name}' exactly, but we have these similar products:\n\n"
                    for product in similar_products:
                        stock_status = "In stock" if product.stock_quantity > 0 else "Out of stock"
                        product_info += f"- {product.name}: {product.price} {product.currency} ({stock_status})\n"
            else:
                # No similar products found
                if language == "ar":
                    product_info = f"عذرًا، لم نتمكن من العثور على '{extracted_product_name}' أو أي منتجات مشابهة. هل يمكنني مساعدتك في البحث عن شيء آخر؟"
                else:
                    product_info = f"Sorry, we couldn't find '{extracted_product_name}' or any similar products. Can I help you look for something else?"
        elif products:
            # Create a general product info text if we have products but couldn't extract a specific name
            if language == "ar":
                product_info = "المنتجات المتوفرة لدينا:\n"
            else:
                product_info = "Available products:\n"
                
            for product in products:
                stock_status = "In stock" if product.stock_quantity > 0 else "Out of stock"
                if language == "ar":
                    stock_status = "متوفر" if product.stock_quantity > 0 else "غير متوفر"
                    product_info += f"- {product.name}: {product.price} {product.currency} ({stock_status})\n"
                else:
                    product_info += f"- {product.name}: {product.price} {product.currency} ({stock_status})\n"
        else:
            # No products available at all
            if language == "ar":
                product_info = "لا توجد منتجات متاحة حاليًا."
            else:
                product_info = "No products available at this time."

    # First search with language filter
    search_results = rag_service.search_similar(user_message, top_k=2, language=language)
    
    # If no good results, try searching across all languages
    if not search_results or len(search_results) == 0 or search_results[0].get('score', 1.0) > 0.7:
        print(f"No good results in {language}, searching across all languages")
        search_results = rag_service.search_similar(user_message, top_k=3, language=None)
    
    retrieved_context = None
    intent = "knowledge_base_query"
    
    # Extract text from search results
    texts = []
    if search_results:
        for result in search_results:
            if isinstance(result, dict) and "text" in result:
                texts.append(result["text"])
                print(f"--- Found text result: {result['text'][:100]}... ---")
    
    # Prepare the prompt with context
    if retrieved_context:
        # Add language instruction based on detected language
        lang_instruction = ""
        if language == "ar":
            lang_instruction = "Please respond in Arabic."
        elif language == "en":
            lang_instruction = "Please respond in English."
            
        prompt = f"""You are a helpful e-commerce support assistant. Use the following context to answer the user's question. If you don't know the answer based on the context, just say you don't have that information. {lang_instruction}

Context: {retrieved_context}

User: {user_message}
"""
    else:
        # Add language instruction based on detected language
        lang_instruction = ""
        if language == "ar":
            lang_instruction = "Please respond in Arabic."
        elif language == "en":
            lang_instruction = "Please respond in English."
            
        prompt = f"""You are a helpful e-commerce support assistant. Answer the user's question to the best of your ability. If you don't know the answer, just say you don't have that information. {lang_instruction}

User: {user_message}
"""

    # Combine texts into a single context
    if texts:
        retrieved_context = "\n\n".join(texts)
    
    # Add product information to the context if available
    if product_info and retrieved_context:
        retrieved_context = f"{retrieved_context}\n\n{product_info}"
    elif product_info:
        retrieved_context = product_info
    
    # 3. Prepare initial state for the graph
    initial_state: ConversationState = {
        "messages": history,
        "user_message": user_message,
        "intent": intent,
        "retrieved_context": retrieved_context,
        "action_result": None,
        "language": language,  # Pass language to the graph
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

class MessageModel(BaseModel):
    type: str
    content: str
    extras: dict = {}

@router.get("/chat/history", response_model=List[MessageModel])
async def get_chat_history(session_id: str = Depends(get_session_id)):
    history = load_history(session_id)
    messages = []
    for m in history:
        if isinstance(m, HumanMessage):
            messages.append({"type": "user", "content": m.content, "extras": {}})
        elif isinstance(m, AIMessage):
            messages.append({"type": "bot", "content": m.content, "extras": {}})
    if not messages:
        messages.append({
            "type": "bot",
            "content": "Hello! I'm your E-Commerce support assistant powered by LangGraph. How can I help you today?",
            "extras": {}
        })
    return messages

@router.post("/chat/clear")
async def clear_chat_history(session_id: str = Depends(get_session_id)):
    save_history(session_id, [])
    return {"success": True}