from fastapi import APIRouter, Request, Depends, HTTPException, status, Response, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel
import os
import json
from pathlib import Path
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

# Import bot settings utility
from app.core.bot_settings import get_bot_settings, save_bot_settings, update_bot_settings, get_bot_settings_model
from app.core.db.database import get_db

# Import templates from the centralized configuration
from app.core.template_config import templates

router = APIRouter(tags=["dashboard"])

# Bot configuration data is now loaded dynamically from the database in each endpoint

# Helper function to format bot settings for the UI
def format_bot_config(db_settings):
    return {
        "basic": {
            "bot_name": db_settings.bot_name,
            "welcome_message": db_settings.welcome_message,
            "fallback_message": db_settings.fallback_message,
            "quick_actions": db_settings.quick_actions or [
                {"label": "Track Order", "value": "Track my order"},
                {"label": "Return Item", "value": "I want to return an item"},
                {"label": "Talk to Human", "value": "I want to talk to a human agent"}
            ]
        },
        "advanced": db_settings.advanced_settings or {
            "session_timeout": 30,
            "max_conversation_turns": 20,
            "features": {
                "product_recommendations": True,
                "order_tracking": True,
                "returns_processing": True,
                "collect_feedback": True,
                "human_handoff": True
            }
        },
        "appearance": {
            "primary_color": "#0d6efd",
            "chat_position": "Bottom Right",
            "avatar_url": "https://ui-avatars.com/api/?name=Bot&background=0D8ABC&color=fff"
        }
    }

# Mock data for knowledge base
mock_knowledge_sources = [
    {
        "name": "Product Information",
        "description": "Contains details about all products, specifications, and pricing.",
        "status": "Active",
        "entries": 42
    },
    {
        "name": "Shipping Policies",
        "description": "Information about shipping methods, timeframes, and costs.",
        "status": "Active",
        "entries": 15
    },
    {
        "name": "Return Policies",
        "description": "Guidelines for product returns, refunds, and exchanges.",
        "status": "Active",
        "entries": 18
    },
    {
        "name": "FAQ Database",
        "description": "Frequently asked questions and their answers.",
        "status": "Active",
        "entries": 37
    },
    {
        "name": "Payment Options",
        "description": "Information about accepted payment methods and processing.",
        "status": "Inactive",
        "entries": 12
    }
]

mock_product_entries = [
    {
        "name": "Wireless Earbuds",
        "content": "Our wireless earbuds feature high-quality sound, long battery life (up to 8 hours), and are water-resistant (IPX5 rating). They come with a charging case that provides an additional 24 hours of battery life.",
        "tags": ["earbuds", "wireless", "audio"]
    },
    {
        "name": "Smart Watch",
        "content": "patterns. It has a battery life of up to 7 days and is compatible with both iOS and Android devices. The watch is water-resistant up to 50 meters.",
        "tags": ["watch", "fitness", "wearable"]
    },
    {
        "name": "Bluetooth Speaker",
        "content": "Our portable Bluetooth speaker delivers rich, room-filling sound with deep bass. It's waterproof (IPX7 rated) and has a battery life of up to 12 hours. The speaker can also be paired with a second unit for stereo sound.",
        "tags": ["speaker", "bluetooth", "audio"]
    },
    {
        "name": "Portable Charger",
        "content": "Our portable charger has a 10,000mAh capacity, enough to fully charge most smartphones 2-3 times. It features fast charging technology and dual USB ports for charging multiple devices simultaneously.",
        "tags": ["charger", "portable", "power"]
    }
]

@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """
    Enhanced landing page for the e-commerce support bot
    """
    return templates.TemplateResponse(request, "enhanced_landing.html")

@router.get("/langgraph-chat-test", response_class=HTMLResponse)
async def customer_support_bot(request: Request):
    """
    Customer-facing support bot interface
    """
    return templates.TemplateResponse(request, "langgraph_chat_test.html")



@router.get("/dashboard")
async def dashboard(request: Request):
    """
    Redirect dashboard to bot-config page
    """
    return RedirectResponse(url="/bot-config")

@router.get("/bot-config", response_class=HTMLResponse)
async def bot_config(request: Request, db: Session = Depends(get_db)):
    """
    Bot configuration page
    """
    # Get bot settings from database
    db_settings = get_bot_settings_model(db)
    
    # Format settings for UI
    bot_config = format_bot_config(db_settings)
    
    return templates.TemplateResponse(request, "bot_config.html", {
        "bot_config": bot_config
    })

@router.get("/knowledge-base", response_class=HTMLResponse)
async def knowledge_base(request: Request):
    """
    Knowledge base management page
    """
    # Import the functions from the milvus_client module
    from app.services.milvus_client import connect_to_milvus, get_all_entries
    
    try:
        # First try to connect to Milvus
        connect_to_milvus()
        
        # Fetch real entries from Milvus vector store
        vector_entries = get_all_entries()
        
        # Format the entries for the template
        formatted_entries = []
        for entry in vector_entries:
            # Extract the text content
            content = entry.get("text", "")
            # Generate a title from the first 30 characters of content
            title = content[:30] + "..." if len(content) > 30 else content
            
            formatted_entries.append({
                "name": title,
                "content": content,
                "tags": ["vector-store"]
            })
        
        # Log the number of entries found
        print(f"Found {len(formatted_entries)} entries in vector store")
    except Exception as e:
        # If there's an error fetching from Milvus, log the error and return empty list
        import traceback
        print(f"Error fetching from vector store: {e}\n{traceback.format_exc()}")
        formatted_entries = []
    
    return templates.TemplateResponse(request, "knowledge_base.html", {
        "sources": [],  # No mock sources, will be loaded via JavaScript
        "entries": formatted_entries
    })

# @router.get("/chat-test")
# async def chat_test(request: Request):
#     """
#     Redirect to LangGraph chat testing interface
#     """
#     return RedirectResponse(url="/langgraph-chat-test", status_code=status.HTTP_301_MOVED_PERMANENTLY)

@router.get("/langgraph-chat-test", response_class=HTMLResponse)
async def langgraph_chat_test(request: Request):
    """
    LangGraph chat testing interface
    """
    return templates.TemplateResponse(request, "langgraph_chat_test.html", {
        "config": bot_config
    })



# API endpoints for dashboard functionality

class BotMessageRequest(BaseModel):
    message: str

@router.post("/api/bot/message")
async def bot_message(request: BotMessageRequest):
    """
    Process a message from the customer support bot
    """
    # Simple mock response with predefined answers based on keywords
    message = request.message.lower()
    
    if "track" in message or "order" in message:
        reply = "Your order is currently in transit and should arrive within 2-3 business days."
        quick_actions = [
            {"label": "Delivery Details", "value": "Can I get more details about the delivery?"},
            {"label": "Change Address", "value": "I need to change my delivery address"}
        ]
    elif "return" in message:
        reply = "You can return any item within 30 days of purchase. Would you like me to guide you through the return process?"
        quick_actions = [
            {"label": "Start Return", "value": "Yes, help me start a return"},
            {"label": "Return Policy", "value": "Tell me more about your return policy"}
        ]
    elif "human" in message or "agent" in message:
        reply = "I'll connect you with a human agent. Please note that the wait time is approximately 5 minutes. Would you like to proceed?"
        quick_actions = [
            {"label": "Yes, connect me", "value": "Yes, connect me to an agent"},
            {"label": "No, continue with bot", "value": "No, I'll continue with you"}
        ]
    else:
        reply = "I'm here to help with order tracking, returns, and connecting you to our team. What would you like assistance with?"
        quick_actions = [
            {"label": "Track Order", "value": "Track my order"},
            {"label": "Return Item", "value": "I want to return an item"},
            {"label": "Talk to Human", "value": "I want to talk to a human agent"}
        ]
    
    return {
        "reply": reply,
        "quick_actions": quick_actions
    }

class BotConfigUpdateRequest(BaseModel):
    basic: Optional[Dict[str, Any]] = None
    advanced: Optional[Dict[str, Any]] = None
    appearance: Optional[Dict[str, Any]] = None

@router.post("/api/dashboard/bot-config")
async def update_bot_config(config: BotConfigUpdateRequest, db: Session = Depends(get_db)):
    """
    Update bot configuration
    """
    # Get current settings from database
    db_settings = get_bot_settings_model(db)
    
    # Prepare updated settings
    bot_name = None
    welcome_message = None
    fallback_message = None
    quick_actions = None
    advanced_settings = None
    
    if config.basic:
        bot_name = config.basic.get("bot_name")
        welcome_message = config.basic.get("welcome_message")
        fallback_message = config.basic.get("fallback_message")
        quick_actions = config.basic.get("quick_actions")
    
    if config.advanced:
        advanced_settings = config.advanced
    
    # Update settings in database
    success = update_bot_settings(
        bot_name=bot_name,
        welcome_message=welcome_message,
        fallback_message=fallback_message,
        quick_actions=quick_actions,
        advanced_settings=advanced_settings,
        db=db
    )
    
    if success:
        return {"status": "success", "message": "Bot configuration updated successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to save bot configuration")

class KnowledgeSourceRequest(BaseModel):
    name: str
    description: str
    status: str = "Active"

@router.post("/api/dashboard/knowledge-source")
async def add_knowledge_source(source: KnowledgeSourceRequest):
    """
    Add a new knowledge source
    """
    # In a real implementation, this would add the source to a database
    new_source = {
        "name": source.name,
        "description": source.description,
        "status": source.status,
        "entries": 0
    }
    mock_knowledge_sources.append(new_source)
    
    return {"status": "success", "message": "Knowledge source added successfully", "source": new_source}

class KnowledgeEntryRequest(BaseModel):
    source_name: str
    name: str
    content: str
    tags: List[str] = []

@router.post("/api/dashboard/knowledge-entry")
async def add_knowledge_entry(entry: KnowledgeEntryRequest):
    """
    Add a new knowledge entry to a source
    """
    # In a real implementation, this would add the entry to a database
    new_entry = {
        "name": entry.name,
        "content": entry.content,
        "tags": entry.tags
    }
    
    # Update the entry count for the source
    for source in mock_knowledge_sources:
        if source["name"] == entry.source_name:
            source["entries"] += 1
            break
    
    mock_product_entries.append(new_entry)
    
    return {"status": "success", "message": "Knowledge entry added successfully", "entry": new_entry}
