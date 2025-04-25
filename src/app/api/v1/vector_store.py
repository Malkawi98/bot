from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from app.services.milvus_client import insert_embedding, get_embedding, search_embedding, get_all_entries, connect_to_milvus

router = APIRouter(tags=["vector-store"])

class VectorStoreAddRequest(BaseModel):
    text: str

class VectorStoreSearchRequest(BaseModel):
    query: str
    top_k: int = 5

@router.post("/vector-store/add", response_model=Dict[str, Any])
async def add_to_vector_store(request: VectorStoreAddRequest):
    """Add text to the vector store"""
    try:
        # Get embedding for the text
        embedding = get_embedding(request.text)
        
        # Debug information
        print(f"Embedding type: {type(embedding)}, length: {len(embedding) if isinstance(embedding, list) else 'N/A'}")
        
        # Validate embedding format
        if not isinstance(embedding, list):
            raise ValueError("Embedding must be a list of floats")
        
        # Use the direct insert_embedding function for single items
        # This is more reliable than the batch function for single items
        from app.services.milvus_client import insert_embedding
        insert_embedding(embedding, request.text)
        
        return {
            "success": True,
            "message": "Text added to vector store successfully"
        }
    except ValueError as e:
        # Client error - bad input
        raise HTTPException(
            status_code=400,
            detail=f"Error adding to vector store: {str(e)}"
        )
    except Exception as e:
        # Server error - log the full error
        import traceback
        print(f"Vector store error: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,  # Changed to 500 to reflect server error
            detail=f"Server error processing vector store request: {str(e)}"
        )

@router.post("/vector-store/search", response_model=Dict[str, Any])
async def search_vector_store(request: VectorStoreSearchRequest):
    """Search the vector store for similar texts"""
    try:
        # Get embedding for the query
        embedding = get_embedding(request.query)
        
        # Debug information
        print(f"Search query embedding type: {type(embedding)}, length: {len(embedding) if isinstance(embedding, list) else 'N/A'}")
        
        # Ensure embedding is in the correct format for search
        if not isinstance(embedding, list):
            raise ValueError("Embedding must be a list of floats")
        
        # Search for similar embeddings
        results = search_embedding(embedding, request.top_k)
        
        # Extract the text results
        texts = []
        if results and len(results) > 0:
            for hits in results:
                for hit in hits:
                    texts.append({
                        "text": hit.entity.get("text"),
                        "score": hit.distance
                    })
        
        return {
            "success": True,
            "results": texts
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to search vector store: {str(e)}"
        )

@router.get("/vector-store/all", response_model=Dict[str, Any])
async def get_all_vector_store_entries():
    """Get all entries from the vector store"""
    try:
        # Get all entries from the vector store
        entries = get_all_entries()
        
        # Format the entries for the response
        formatted_entries = []
        for entry in entries:
            formatted_entries.append({
                "id": entry.get("id", ""),
                "text": entry.get("text", ""),
                "title": f"Entry #{entry.get('id', '')}" if entry.get("id") else "Knowledge Entry",
                "content": entry.get("text", ""),
                "tags": ["vector-store"]
            })
        
        return {
            "success": True,
            "count": len(formatted_entries),
            "entries": formatted_entries
        }
    except Exception as e:
        import traceback
        print(f"Error getting all vector store entries: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get vector store entries: {str(e)}"
        )

@router.get("/vector-store/status", response_model=Dict[str, Any])
async def check_vector_store_status():
    """Check the status of the vector store connection"""
    try:
        # Try to connect to Milvus
        connect_to_milvus()
        
        # If we get here, the connection was successful
        return {
            "success": True,
            "status": "connected",
            "message": "Successfully connected to vector store"
        }
    except Exception as e:
        import traceback
        print(f"Error connecting to vector store: {str(e)}\n{traceback.format_exc()}")
        
        # Return a 200 response with connection failure info rather than an error
        # This allows the frontend to handle the case gracefully
        return {
            "success": False,
            "status": "disconnected",
            "message": f"Failed to connect to vector store: {str(e)}"
        }
