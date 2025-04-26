"""
Debug endpoints for the vector store.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.core.db.database import get_db
from app.services.rag import RAGService

router = APIRouter(tags=["vector-store-debug"])

@router.get("/vector-store/debug")
async def debug_vector_store(
    query: str = Query(..., description="Query to search for in the vector store"),
    top_k: int = Query(5, description="Number of results to return"),
    language: str = Query(None, description="Language filter (en or ar)"),
    db: Session = Depends(get_db)
):
    """
    Debug endpoint for searching the vector store directly.
    """
    try:
        rag_service = RAGService()
        results = rag_service.search_similar(query, top_k=top_k, language=language)
        
        return {
            "query": query,
            "language": language,
            "results_count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching vector store: {str(e)}")
