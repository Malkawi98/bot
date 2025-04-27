from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from app.services.milvus_client import insert_embedding, get_embedding, search_embedding, get_all_entries, connect_to_milvus, reset_collection, COLLECTION_NAME
from pymilvus import Collection, utility

router = APIRouter(tags=["vector-store"])

class VectorStoreAddRequest(BaseModel):
    text: str
    language: str = "en"  # Default to English, can be 'ar' for Arabic

class VectorStoreSearchRequest(BaseModel):
    query: str
    top_k: int = 5
    language: str = None  # Optional language filter, if None will search across all languages

@router.post("/vector-store/add", response_model=Dict[str, Any])
async def add_to_vector_store(request: VectorStoreAddRequest):
    """Add text to the vector store"""
    try:
        # Get embedding for the text
        embedding = get_embedding(request.text)
        
        # Debug information
        print(f"Embedding type: {type(embedding)}, length: {len(embedding) if isinstance(embedding, list) else 'N/A'}")
        print(f"Adding text in language: {request.language}")
        
        # Validate embedding format
        if not isinstance(embedding, list):
            raise ValueError("Embedding must be a list of floats")
        
        # Use the direct insert_embedding function for single items with language metadata
        # This is more reliable than the batch function for single items
        from app.services.milvus_client import insert_embedding
        insert_embedding(embedding, request.text, language=request.language)
        
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
        if request.language:
            print(f"Searching with language filter: {request.language}")
        else:
            print("Searching across all languages")
        
        # Ensure embedding is in the correct format for search
        if not isinstance(embedding, list):
            raise ValueError("Embedding must be a list of floats")
        
        # Prepare language filter if specified
        filter_expr = None
        if request.language:
            filter_expr = f"language == '{request.language}'"
        
        # Search for similar embeddings with optional language filter
        results = search_embedding(embedding, request.top_k, filter_expr=filter_expr)
        
        # Extract the text results
        texts = []
        if results and len(results) > 0:
            for hits in results:
                for hit in hits:
                    texts.append({
                        "text": hit.entity.get("text"),
                        "language": hit.entity.get("language", "en"),
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
        # Connect to Milvus and print debug info
        connect_to_milvus()
        print(f"Connected to Milvus, checking collection: {COLLECTION_NAME}")
        
        # Check if collection exists
        collections = utility.list_collections()
        print(f"Available collections: {collections}")
        
        if COLLECTION_NAME not in collections:
            print(f"Warning: Collection {COLLECTION_NAME} not found in Milvus")
            return {
                "success": False,
                "message": f"Collection {COLLECTION_NAME} not found",
                "count": 0,
                "entries": []
            }
            
        # Get collection stats
        try:
            col = Collection(COLLECTION_NAME)
            print(f"Collection {COLLECTION_NAME} has {col.num_entities} entities")
        except Exception as e:
            print(f"Error getting collection stats: {e}")
        
        # Get all entries from the vector store
        entries = get_all_entries()
        print(f"Retrieved {len(entries)} entries from get_all_entries")
        
        # Format the entries for the response
        formatted_entries = []
        for i, entry in enumerate(entries, 1):
            # Extract a clean entry number for display
            original_id = entry.get("id", "")
            display_id = i  # Use the enumeration index as a clean display ID
            
            formatted_entries.append({
                "id": original_id,  # Keep the original ID for database operations
                "display_id": display_id,  # Add a clean display ID for UI
                "text": entry.get("text", ""),
                "language": entry.get("language", "en"),
                "title": f"Entry #{display_id}",
                "content": entry.get("text", ""),
                "tags": ["vector-store", entry.get("language", "en")]
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

@router.post("/vector-store/reset", response_model=Dict[str, Any])
async def reset_vector_store():
    """Reset the vector store by dropping and recreating the collection"""
    try:
        # Reset the collection
        reset_collection()
        
        return {
            "success": True,
            "message": "Vector store has been reset successfully"
        }
    except Exception as e:
        import traceback
        print(f"Error resetting vector store: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset vector store: {str(e)}"
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
