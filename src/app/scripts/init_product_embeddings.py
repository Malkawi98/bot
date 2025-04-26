"""
Initialize the product embeddings collection in Milvus.
This script syncs all products from PostgreSQL to the Milvus vector database.
"""
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy.orm import Session
from app.core.db.database import sync_engine, sync_session
from app.services.product_embedding import ProductEmbeddingService

def init_product_embeddings():
    """Initialize the product embeddings collection by syncing all products from PostgreSQL."""
    print("Initializing product embeddings collection in Milvus...")
    
    # Create a database session
    db = sync_session()
    
    try:
        # Create the product embedding service
        embedding_service = ProductEmbeddingService(db)
        
        # Sync all products to Milvus
        result = embedding_service.sync_all_products()
        
        if result:
            print("Successfully synchronized all products to Milvus!")
        else:
            print("Failed to synchronize products to Milvus.")
    except Exception as e:
        print(f"Error initializing product embeddings: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_product_embeddings()
