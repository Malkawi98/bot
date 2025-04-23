from fastapi import APIRouter, Request, Depends, HTTPException, status, Response, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel
import os
import json
from pathlib import Path
import uuid
from datetime import datetime

# Import bot settings utility
from app.core.bot_settings import get_bot_settings, save_bot_settings, update_bot_settings

# Setup templates
templates_dir = Path(__file__).resolve().parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter(tags=["dashboard"])

# Bot configuration data

# Use bot settings utility to get bot configuration
bot_settings = get_bot_settings()

# Format bot settings to match the expected structure in the UI
bot_config = {
    "basic": {
        "bot_name": bot_settings.get("bot_name", "E-Commerce Support Bot"),
        "welcome_message": bot_settings.get("welcome_message", "Hello! I'm your support assistant. How can I help you today?"),
        "fallback_message": bot_settings.get("fallback_message", "I'm sorry, I couldn't understand your request. Could you please rephrase or select one of the quick options below?"),
        "quick_actions": bot_settings.get("quick_actions", [
            {"label": "Track Order", "value": "Track my order"},
            {"label": "Return Item", "value": "I want to return an item"},
            {"label": "Talk to Human", "value": "I want to talk to a human agent"}
        ])
    },
    "advanced": bot_settings.get("advanced_settings", {
        "session_timeout": 30,
        "max_conversation_turns": 20,
        "features": {
            "product_recommendations": True,
            "order_tracking": True,
            "returns_processing": True,
            "collect_feedback": True,
            "human_handoff": True
        }
    }),
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
        "content": "Our smart watch tracks fitness activities, heart rate, and sleep patterns. It has a battery life of up to 7 days and is compatible with both iOS and Android devices. The watch is water-resistant up to 50 meters.",
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
    return templates.TemplateResponse("enhanced_landing.html", {"request": request})

@router.get("/customer-support-bot", response_class=HTMLResponse)
async def customer_support_bot(request: Request):
    """
    Customer-facing support bot interface
    """
    return templates.TemplateResponse("customer_support_bot.html", {"request": request})



@router.get("/dashboard")
async def dashboard(request: Request):
    """
    Redirect dashboard to bot-config page
    """
    return RedirectResponse(url="/bot-config")

@router.get("/bot-config", response_class=HTMLResponse)
async def bot_config(request: Request):
    """
    Bot configuration page
    """
    return templates.TemplateResponse("bot_config.html", {
        "request": request,
        "config": bot_config
    })

@router.get("/knowledge-base", response_class=HTMLResponse)
async def knowledge_base(request: Request):
    """
    Knowledge base management page
    """
    return templates.TemplateResponse("knowledge_base.html", {
        "request": request,
        "sources": mock_knowledge_sources,
        "entries": mock_product_entries
    })

@router.get("/chat-test", response_class=HTMLResponse)
async def chat_test(request: Request):
    """
    Chat testing interface
    """
    return templates.TemplateResponse("chat_test.html", {
        "request": request,
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
async def update_bot_config(config: BotConfigUpdateRequest):
    """
    Update bot configuration
    """
    # Update the bot configuration in memory
    if config.basic:
        bot_config["basic"].update(config.basic)
    if config.advanced:
        bot_config["advanced"].update(config.advanced)
    if config.appearance:
        bot_config["appearance"].update(config.appearance)
    
    # Save the updated configuration to the JSON file
    updated_settings = {
        "bot_name": bot_config["basic"]["bot_name"],
        "welcome_message": bot_config["basic"]["welcome_message"],
        "fallback_message": bot_config["basic"]["fallback_message"],
        "quick_actions": bot_config["basic"]["quick_actions"],
        "advanced_settings": bot_config["advanced"],
        "appearance": bot_config["appearance"]
    }
    
    # Save to the JSON file
    success = save_bot_settings(updated_settings)
    
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
