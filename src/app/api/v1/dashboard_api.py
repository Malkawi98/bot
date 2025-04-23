from fastapi import APIRouter, Depends, HTTPException, status, Header, File, UploadFile, Form
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.core.security import oauth2_scheme, jwt, SECRET_KEY, ALGORITHM, TokenType
from app.services.bot_service import BotService
from app.services.rag import RAGService
from app.services.milvus_client import list_collections, search_embedding, insert_embedding, drop_collection
from datetime import datetime, timedelta
import json
import uuid
import io
import os
import tempfile
from urllib.parse import urlparse

# Function to get the current user from the token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("token_type")
        if username is None or token_type != TokenType.ACCESS:
            raise credentials_exception
        return {"username": username}
    except jwt.JWTError:
        raise credentials_exception

router = APIRouter(tags=["dashboard-api"])

# Initialize services
bot_service = BotService()
rag_service = RAGService()

# Data models for API requests and responses
class BotConfigUpdateRequest(BaseModel):
    bot_name: Optional[str] = None
    welcome_message: Optional[str] = None
    fallback_message: Optional[str] = None
    quick_actions: Optional[List[Dict[str, str]]] = None
    session_timeout: Optional[int] = None
    features: Optional[Dict[str, bool]] = None
    appearance: Optional[Dict[str, Any]] = None

class BotConfigResponse(BaseModel):
    success: bool
    message: str
    config: Dict[str, Any]

class KnowledgeSourceRequest(BaseModel):
    name: str
    description: str
    source_type: str
    url: Optional[str] = None
    content: Optional[str] = None

class KnowledgeSourceResponse(BaseModel):
    success: bool
    message: str
    source_id: Optional[str] = None

class KnowledgeEntryRequest(BaseModel):
    source_id: str
    title: str
    content: str
    tags: List[str] = []
    
class ImportUrlRequest(BaseModel):
    url: str
    source_id: Optional[str] = None

class KnowledgeEntryResponse(BaseModel):
    success: bool
    message: str
    entry_id: Optional[str] = None

class AnalyticsResponse(BaseModel):
    success: bool
    total_conversations: int
    average_satisfaction: float
    popular_topics: List[Dict[str, Any]]
    response_times: Dict[str, float]

# Mock data for bot configuration
mock_bot_config = {
    "bot_name": "E-Commerce Support Bot",
    "welcome_message": "Hello! I'm your support assistant. How can I help you today?",
    "fallback_message": "I'm sorry, I couldn't understand your request. Could you please rephrase or select one of the quick options below?",
    "quick_actions": [
        {"label": "Track Order", "value": "Track my order"},
        {"label": "Return Item", "value": "I want to return an item"},
        {"label": "Talk to Human", "value": "I want to talk to a human agent"}
    ],
    "session_timeout": 30,
    "features": {
        "product_recommendations": True,
        "order_tracking": True,
        "returns_processing": True,
        "collect_feedback": True,
        "human_handoff": True
    },
    "appearance": {
        "primary_color": "#0d6efd",
        "chat_position": "Bottom Right",
        "avatar_url": "https://ui-avatars.com/api/?name=Bot&background=0D8ABC&color=fff"
    }
}

# Database for knowledge sources (in-memory for demo purposes)
knowledge_sources_db = [
    {
        "id": "ks-001",
        "name": "Product Information",
        "description": "Contains details about all products, specifications, and pricing.",
        "source_type": "manual",
        "entries": 0,
        "last_updated": datetime.now().isoformat()
    },
    {
        "id": "ks-002",
        "name": "Shipping Policies",
        "description": "Information about shipping methods, timeframes, and costs.",
        "source_type": "url",
        "url": "https://example.com/shipping",
        "entries": 0,
        "last_updated": datetime.now().isoformat()
    }
]

# Mock data for analytics
mock_analytics = {
    "total_conversations": 1285,
    "average_satisfaction": 92.5,
    "popular_topics": [
        {"topic": "Order Status", "percentage": 35},
        {"topic": "Product Info", "percentage": 25},
        {"topic": "Returns", "percentage": 15},
        {"topic": "Payment", "percentage": 10},
        {"topic": "Shipping", "percentage": 10},
        {"topic": "Other", "percentage": 5}
    ],
    "response_times": {
        "average": 1.2,
        "median": 0.9,
        "p95": 2.5
    },
    "daily_conversations": {
        "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "data": [65, 78, 52, 91, 83, 56, 80]
    },
    "hourly_distribution": {
        "labels": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23"],
        "data": [12, 8, 5, 3, 2, 4, 10, 25, 48, 62, 75, 68, 72, 80, 76, 70, 65, 58, 52, 45, 38, 30, 22, 15]
    }
}

# API Endpoints

# Import random for generating mock data
import random

@router.get("/analytics", response_model=Dict[str, Any])
async def get_analytics():
    """Get bot analytics data"""
    return mock_analytics

@router.get("/analytics/conversations", response_model=Dict[str, Any])
async def get_conversation_analytics():
    """Get detailed conversation analytics"""
    # Generate some mock conversation data for the last 7 days
    today = datetime.now()
    conversations = []
    
    for i in range(7):
        day = today - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        
        # Generate random number of conversations for this day
        num_conversations = random.randint(40, 100)
        
        for j in range(num_conversations):
            conversations.append({
                "id": f"conv-{day_str}-{j}",
                "date": day_str,
                "user_id": f"user_{random.randint(1000, 9999)}",
                "topic": random.choice(["Order Status", "Product Info", "Returns", "Payment", "Shipping", "Other"]),
                "messages": random.randint(3, 15),
                "duration": random.randint(1, 10),
                "satisfaction": random.randint(1, 5),
                "resolved": random.choice([True, False, True, True]),  # Bias towards resolved
            })
    
    return {
        "success": True,
        "total": len(conversations),
        "conversations": conversations[:50]  # Return only the first 50 for pagination
    }

@router.get("/analytics/performance", response_model=Dict[str, Any])
async def get_performance_analytics():
    """Get bot performance analytics"""
    # Generate performance data for the last 30 days
    today = datetime.now()
    daily_data = []
    
    for i in range(30):
        day = today - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        
        daily_data.append({
            "date": day_str,
            "conversations": random.randint(40, 100),
            "avg_response_time": round(random.uniform(0.8, 2.0), 2),
            "satisfaction": round(random.uniform(85, 98), 1),
            "resolution_rate": round(random.uniform(75, 95), 1)
        })
    
    return {
        "success": True,
        "performance_data": daily_data
    }

# Vector store knowledge management endpoints
@router.get("/vector-store/entries", response_model=List[Dict[str, Any]])
async def get_vector_store_entries(query: str = "", top_k: int = 10):
    """Get entries from the vector store based on a search query"""
    try:
        if not query.strip():
            # Return empty list if no query is provided
            return []
        
        # Use the RAG service to search for similar entries
        results = rag_service.search_similar(query, top_k=top_k)
        
        # Format the results
        entries = []
        for i, result in enumerate(results[0]):
            entry = {
                "id": f"vs-{result.id}",
                "title": result.entity.get('text', '')[:50] + "...",  # Use first 50 chars as title
                "content": result.entity.get('text', ''),
                "similarity": float(result.distance),
                "tags": ["vector-store"],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            entries.append(entry)
        
        return entries
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching vector store: {str(e)}")

@router.post("/vector-store/add", response_model=Dict[str, Any])
async def add_to_vector_store(content: Dict[str, str]):
    """Add content to the vector store"""
    try:
        text = content.get("text", "")
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text content is required")
        
        # Add the text to the vector store
        rag_service.add_text_to_milvus(text)
        
        return {
            "success": True,
            "message": "Content added to vector store successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding to vector store: {str(e)}")

# Knowledge entry management endpoints
@router.get("/knowledge-entries", response_model=List[Dict[str, Any]])
async def get_knowledge_entries(source_id: Optional[str] = None, query: Optional[str] = None):
    """Get knowledge entries, optionally filtered by source ID or search query"""
    # If a query is provided, use the RAG service to search for similar entries
    if query and query.strip():
        try:
            # Use the RAG service to search for similar entries
            results = rag_service.search_similar(query, top_k=10)
            
            # Format the results
            entries = []
            for i, result in enumerate(results[0]):
                entry = {
                    "id": f"vs-{result.id}",
                    "source_id": source_id if source_id else "vector-store",
                    "title": result.entity.get('text', '')[:50] + "...",  # Use first 50 chars as title
                    "content": result.entity.get('text', ''),
                    "tags": ["vector-store"],
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "similarity": float(result.distance)
                }
                entries.append(entry)
            
            return entries
        except Exception as e:
            # If search fails, log the error and return empty list
            print(f"Error searching vector store: {str(e)}")
            return []
    
    # If no query, return empty list - in a real implementation, this would query a database
    # for entries associated with the specified source_id
    return []

@router.delete("/knowledge-entries/{entry_id}", response_model=Dict[str, Any])
async def delete_knowledge_entry(entry_id: str):
    """Delete a knowledge entry"""
    # In a real implementation, this would delete the entry from the vector store
    # Currently, Milvus doesn't support deleting individual entries easily
    # So we'll just return success for the demo
    
    # If the entry ID starts with 'vs-', it's from the vector store
    if entry_id.startswith('vs-'):
        try:
            # In a real implementation, we would delete the entry from the vector store
            # For now, we'll just return success
            return {
                "success": True,
                "message": "Knowledge entry deleted successfully"
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete entry from vector store: {str(e)}"
            )
    
    # For other entry IDs, just return success
    return {
        "success": True,
        "message": "Knowledge entry deleted successfully"
    }

@router.get("/knowledge-sources/{source_id}", response_model=Dict[str, Any])
async def get_knowledge_source(source_id: str):
    """Get a specific knowledge source"""
    for source in knowledge_sources_db:
        if source["id"] == source_id:
            return source
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Knowledge source with ID {source_id} not found"
    )

@router.post("/knowledge-entries", response_model=KnowledgeEntryResponse)
async def create_knowledge_entry(entry: KnowledgeEntryRequest):
    """Create a new knowledge entry"""
    # Find the source
    source_found = False
    for source in knowledge_sources_db:
        if source["id"] == entry.source_id:
            source_found = True
            source["entries"] += 1
            source["last_updated"] = datetime.now().isoformat()
            break
    
    if not source_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge source with ID {entry.source_id} not found"
        )
    
    # Add the entry to the vector store
    try:
        # Use the RAG service to add the entry to the vector store
        rag_service.add_text_to_milvus(entry.content)
        
        # Generate a unique ID for the entry
        entry_id = f"ke-{uuid.uuid4().hex[:8]}"
        
        return {
            "success": True,
            "message": "Knowledge entry created successfully",
            "entry_id": entry_id
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add entry to knowledge base: {str(e)}"
        )

# Knowledge sources endpoints
@router.get("/knowledge-sources", response_model=List[Dict[str, Any]])
async def get_knowledge_sources():
    """Get all knowledge sources"""
    return knowledge_sources_db

@router.post("/knowledge-sources", response_model=KnowledgeSourceResponse)
async def create_knowledge_source(source: KnowledgeSourceRequest):
    """Create a new knowledge source"""
    # Generate a unique ID for the new source
    source_id = f"ks-{uuid.uuid4().hex[:8]}"
    
    new_source = {
        "id": source_id,
        "name": source.name,
        "description": source.description,
        "source_type": source.source_type,
        "entries": 0,
        "last_updated": datetime.now().isoformat()
    }
    
    # Add URL if provided
    if source.url:
        new_source["url"] = source.url
        
        # If URL is provided and source type is URL, process the content
        try:
            if source.source_type == "url":
                # Use the RAG service to process the URL
                # This would extract content and add it to the vector store
                content = rag_service.get_context_from_url(source.url)
                if content:
                    # Add the content to the vector store
                    rag_service.add_text_to_milvus(content)
                    new_source["entries"] = 1  # At least one entry was added
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to process URL: {str(e)}"
            )
    
    # Add the new source to the database
    knowledge_sources_db.append(new_source)
    
    return {
        "success": True,
        "message": "Knowledge source created successfully",
        "source_id": source_id
    }

# Knowledge import endpoints
@router.post("/knowledge-import/url", response_model=Dict[str, Any])
async def import_from_url(request: ImportUrlRequest):
    """Import knowledge content from a URL"""
    try:
        # Validate URL
        parsed_url = urlparse(request.url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL format"
            )
        
        # Use the RAG service to extract content from the URL
        content = rag_service.get_context_from_url(request.url)
        
        if not content:
            return {
                "success": False,
                "message": "Could not extract content from the URL"
            }
        
        # Add the content to the vector store
        rag_service.add_text_to_milvus(content)
        
        # If a source_id was provided, update its entry count
        if request.source_id:
            for source in knowledge_sources_db:
                if source["id"] == request.source_id:
                    source["entries"] += 1
                    source["last_updated"] = datetime.now().isoformat()
                    break
        
        return {
            "success": True,
            "message": "Content imported successfully from URL",
            "content_length": len(content)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error importing from URL: {str(e)}"
        )

@router.post("/knowledge-import/file", response_model=Dict[str, Any])
async def import_from_file(file: UploadFile = File(...), source_id: Optional[str] = Form(None)):
    """Import knowledge content from an uploaded file"""
    try:
        # Check file extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        allowed_extensions = [".pdf", ".docx", ".txt", ".md", ".csv"]
        
        if file_ext not in allowed_extensions:
            return {
                "success": False,
                "message": f"Unsupported file type. Allowed types: {', '.join(allowed_extensions)}"
            }
        
        # Read the file content
        content = await file.read()
        
        # For text files, directly use the content
        if file_ext in [".txt", ".md", ".csv"]:
            text_content = content.decode("utf-8")
        else:
            # For binary files like PDF and DOCX, we would need specialized parsers
            # For this demo, we'll just return a message that we'd process these files
            return {
                "success": True,
                "message": f"File {file.filename} would be processed in a production environment",
                "file_type": file_ext
            }
        
        # Add the content to the vector store
        rag_service.add_text_to_milvus(text_content)
        
        # If a source_id was provided, update its entry count
        if source_id:
            for source in knowledge_sources_db:
                if source["id"] == source_id:
                    source["entries"] += 1
                    source["last_updated"] = datetime.now().isoformat()
                    break
        
        return {
            "success": True,
            "message": "File imported successfully",
            "filename": file.filename,
            "content_length": len(text_content) if file_ext in [".txt", ".md", ".csv"] else len(content)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error importing file: {str(e)}"
        )

@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics():
    """Get analytics data for the bot"""
    return {
        "success": True,
        **mock_analytics
    }

@router.post("/test-message")
async def test_message(message: Dict[str, str]):
    """Test a message with the bot in the admin interface"""
    if "text" not in message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message text is required"
        )
    
    # Create a test session state
    test_session = {"count": 1, "history": []}
    
    # Process the message using the bot service
    reply, quick_actions, additional_data, confidence = bot_service.process_message(message["text"], test_session)
    
    # Prepare the response
    response = {
        "reply": reply,
        "quick_actions": quick_actions,
        "confidence": confidence,
        "source": "bot_service"
    }
    
    # Add additional data if available
    if additional_data:
        response["additional_data"] = additional_data
    
    return response
