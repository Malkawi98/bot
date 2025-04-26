#!/usr/bin/env python
"""
Test script for product search functionality using the ProductEmbeddingService.
This script tests both English and Arabic product searches in the Milvus vector database.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from app.services.product_embedding import ProductEmbeddingService
from app.core.db.database import sync_session

def test_product_search():
    """Test the product search functionality."""
    db = sync_session()
    try:
        # Initialize the product embedding service with the database session
        product_embedding_service = ProductEmbeddingService(db)
        
        # First, let's check what's in the Milvus collection
        from app.services.milvus_client import search_embedding, get_embedding
        
        print("\n=== Checking Milvus Collection Content ===")
        # Use a generic query to get all products
        generic_query = "product"
        query_embedding = get_embedding(generic_query)
        
        # Search without language filter to see everything
        raw_results = search_embedding(
            embedding=query_embedding,
            top_k=20,  # Get more results to see what's there
            collection_name="product_embeddings",
            filter_expr=None  # No filter to see all entries
        )
        
        print(f"Raw search returned {len(raw_results)} items")
        for i, result in enumerate(raw_results, 1):
            print(f"Item {i}:")
            print(f"  ID: {result.get('id')}")
            print(f"  Score: {result.get('score')}")
            print(f"  Text: {result.get('text')}")
            print(f"  Language: {result.get('language')}")
            print()
        
        # Test English search
        print("\n=== Testing English Product Search ===")
        english_queries = [
            "gaming laptop",
            "high performance laptop",
            "laptop with RTX graphics",
            "XZ2000 laptop",
            "laptop with 32GB RAM"
        ]
        
        for query in english_queries:
            print(f"\nSearching for: '{query}'")
            # Debug the raw search results
            query_embedding = get_embedding(query)
            raw_results = search_embedding(
                embedding=query_embedding,
                top_k=3,
                collection_name="product_embeddings",
                filter_expr="language == 'en'"
            )
            
            print(f"Raw search returned {len(raw_results)} items")
            for i, result in enumerate(raw_results, 1):
                print(f"Item {i}:")
                print(f"  ID: {result.get('id')}")
                print(f"  Score: {result.get('score')}")
                print(f"  Text: {result.get('text')}")
                print(f"  Language: {result.get('language')}")
                
            # Now try the service method
            results = product_embedding_service.search_products(query, language="en", top_k=3)
            if results:
                print(f"Found {len(results)} processed results:")
                for i, result in enumerate(results, 1):
                    print(f"{i}. {result.get('name')} - Score: {result.get('similarity_score', 'N/A')}")
            else:
                print("No processed results found.")
        
        # Test Arabic search with similar debugging
        print("\n=== Testing Arabic Product Search ===")
        arabic_queries = [
            "لابتوب ألعاب",
            "كمبيوتر محمول للألعاب",
            "لابتوب XZ2000"
        ]
        
        for query in arabic_queries:
            print(f"\nSearching for: '{query}'")
            # Debug the raw search results
            query_embedding = get_embedding(query)
            raw_results = search_embedding(
                embedding=query_embedding,
                top_k=3,
                collection_name="product_embeddings",
                filter_expr="language == 'ar'"
            )
            
            print(f"Raw search returned {len(raw_results)} items")
            for i, result in enumerate(raw_results, 1):
                print(f"Item {i}:")
                print(f"  ID: {result.get('id')}")
                print(f"  Score: {result.get('score')}")
                print(f"  Text: {result.get('text')}")
                print(f"  Language: {result.get('language')}")
                
            # Now try the service method
            results = product_embedding_service.search_products(query, language="ar", top_k=3)
            if results:
                print(f"Found {len(results)} processed results:")
                for i, result in enumerate(results, 1):
                    print(f"{i}. {result.get('name')} - Score: {result.get('similarity_score', 'N/A')}")
            else:
                print("No processed results found.")
                
    finally:
        db.close()

if __name__ == "__main__":
    test_product_search()
