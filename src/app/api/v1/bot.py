from fastapi import APIRouter, Request, Cookie, Depends, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from fastapi.templating import Jinja2Templates
from uuid import uuid4
from fastapi import Response
import json
import random
from datetime import datetime, timedelta
from app.services.rag import RAGService

router = APIRouter(tags=["bot"])

# Change template directory for Docker compatibility
templates = Jinja2Templates(directory="src/app/templates")

# Initialize RAG service
rag_service = RAGService()

# In-memory session state (for demo only)
session_states = {}

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
    if not session_id:
        session_id = str(uuid4())
    return session_id

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

from app.services.bot_service import BotService

# Initialize bot service
bot_service = BotService()

@router.post("/bot/message", response_model=BotMessageResponse)
async def bot_message(request: BotMessageRequest, response: Response, session_id: str = Cookie(None)):
    user_message = request.message
    
    # Session state management
    if not session_id or session_id not in session_states:
        session_id = str(uuid4())
        session_states[session_id] = {"count": 0, "history": []}
    
    state = session_states[session_id]
    state["count"] += 1
    
    # Set session cookie
    response.set_cookie(key="session_id", value=session_id, httponly=True, samesite="lax")
    
    # Process the message using the bot service
    reply, quick_actions_data, additional_data, confidence = bot_service.process_message(user_message, state)
    
    # Convert quick actions to the expected format
    quick_actions = [QuickAction(label=qa["label"], value=qa["value"]) for qa in quick_actions_data] if quick_actions_data else None
    
    # Prepare the response
    bot_response = BotMessageResponse(
        reply=reply,
        quick_actions=quick_actions,
        confidence_score=confidence,
        source="bot_service"
    )
    
    # Add product information if available
    if additional_data and "product_info" in additional_data:
        product = additional_data["product_info"]
        bot_response.products = [
            ProductInfo(
                id=product.get("id", "unknown"),
                name=product["name"],
                price=product["price"],
                description=product["description"],
                image_url=f"https://ui-avatars.com/api/?name={product['name']}&size=128"
            )
        ]
    
    # Add order information if available
    if additional_data and "order_info" in additional_data:
        order = additional_data["order_info"]
        bot_response.order_info = OrderInfo(
            order_id=order["order_id"],
            status=order["status"],
            status_description=order["status_description"],
            tracking_number=order["tracking_number"],
            estimated_delivery=order["estimated_delivery"]
        )
    
    # Add recommended products if available
    if additional_data and "recommended_products" in additional_data:
        recommended = additional_data["recommended_products"]
        bot_response.products = [
            ProductInfo(
                id=product.get("id", "unknown"),
                name=product["name"],
                price=product["price"],
                description=f"Category: {product.get('category', 'General')}",
                image_url=f"https://ui-avatars.com/api/?name={product['name']}&size=128"
            ) for product in recommended
        ]
    
    return bot_response

@router.get("/customer-support-bot", response_class=HTMLResponse)
async def customer_support_bot(request: Request):
    return templates.TemplateResponse("customer_support_bot.html", {"request": request}) 