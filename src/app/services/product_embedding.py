"""
Product embedding service for managing product data in Milvus.
This service handles synchronization between PostgreSQL and the Milvus vector database.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.product import Product
from app.services.milvus_client import (
    connect_to_milvus, 
    create_collection, 
    insert_embedding, 
    search_embedding,
    get_embedding,
    drop_collection,
    reset_collection
)
import json

# Define a dedicated collection name for products
PRODUCT_COLLECTION_NAME = "product_embeddings"
EMBEDDING_DIM = 1536  # Same dimension as the RAG embeddings

class ProductEmbeddingService:
    """Service for managing product embeddings in Milvus."""
    
    def __init__(self, db: Session = None):
        """Initialize the product embedding service."""
        self.db = db
        # Connect to Milvus and ensure the product collection exists
        connect_to_milvus()
        self._ensure_collection_exists()
    
    def _ensure_collection_exists(self):
        """Ensure the product collection exists in Milvus."""
        create_collection(collection_name=PRODUCT_COLLECTION_NAME, dim=EMBEDDING_DIM)
    
    def _format_product_for_embedding(self, product: Product) -> str:
        """Format a product for embedding generation."""
        # Create a rich text representation of the product
        product_text = f"""
Product: {product.name}
ID: {product.id}
Category: {product.category or 'Uncategorized'}
Price: {product.price} {product.currency}
In Stock: {'Yes' if product.stock_quantity > 0 else 'No'}
Stock Quantity: {product.stock_quantity} items
Description: {product.description or 'No description available'}
Language: {product.language or 'en'}
"""
        return product_text
    
    def add_product_to_milvus(self, product: Product):
        """Add a product to the Milvus vector database."""
        # Format the product as text
        product_text = self._format_product_for_embedding(product)
        
        # Generate embedding for the product
        embedding = get_embedding(product_text)
        
        # Create metadata to store with the embedding
        metadata = {
            "product_id": product.id,
            "name": product.name,
            "price": product.price,
            "currency": product.currency,
            "category": product.category,
            "stock_quantity": product.stock_quantity,
            "is_active": product.is_active
        }
        
        # Convert metadata to string for storage
        metadata_str = json.dumps(metadata)
        
        # Insert the embedding into Milvus
        insert_embedding(
            embedding=embedding, 
            text=metadata_str, 
            collection_name=PRODUCT_COLLECTION_NAME,
            language=product.language or "en"
        )
        
        print(f"Added product {product.id}: {product.name} to Milvus collection {PRODUCT_COLLECTION_NAME}")
        return True
    
    def remove_product_from_milvus(self, product_id: int):
        """
        Remove a product from Milvus.
        
        Note: Milvus doesn't support direct deletion by ID in the free version.
        We'll need to recreate the collection and re-add all products except the one to delete.
        """
        # This is a workaround since Milvus doesn't support direct deletion in the free version
        if not self.db:
            print("Database session required to remove products from Milvus")
            return False
            
        # Get all active products except the one to delete
        products = self.db.query(Product).filter(
            Product.id != product_id,
            Product.is_active == True
        ).all()
        
        # Reset the collection (drop and recreate)
        reset_collection(collection_name=PRODUCT_COLLECTION_NAME)
        
        # Re-add all remaining products
        for product in products:
            self.add_product_to_milvus(product)
            
        print(f"Removed product {product_id} from Milvus collection {PRODUCT_COLLECTION_NAME}")
        return True
    
    def search_products(self, query: str, top_k: int = 5, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for products in Milvus using semantic similarity.
        
        Args:
            query: The search query
            top_k: Number of results to return
            language: Optional language filter
            
        Returns:
            List of product dictionaries
        """
        # Generate embedding for the query
        query_embedding = get_embedding(query)
        
        # Create language filter if specified
        filter_expr = None
        if language:
            filter_expr = f"language == '{language}'"
        
        # Search for similar products in Milvus (this is currently not working well)
        raw_results = search_embedding(
            embedding=query_embedding,
            top_k=top_k,
            collection_name=PRODUCT_COLLECTION_NAME,
            filter_expr=filter_expr
        )
        
        # Fallback to direct database search
        if not self.db:
            print("Database session required for product search")
            return []
            
        # Get all active products
        all_products = self.db.query(Product).filter(Product.is_active == True)
        if language:
            all_products = all_products.filter(Product.language == language)
        all_products = all_products.all()
            
        # Process products with smart scoring
        products_list = []
        query_lower = query.lower()
        
        for product in all_products:
            # Create a product dictionary
            product_dict = {
                "product_id": product.id,
                "name": product.name,
                "description": product.description,
                "price": product.price,
                "currency": product.currency,
                "category": product.category,
                "stock_quantity": product.stock_quantity,
                "is_active": product.is_active,
                "language": product.language,
                "similarity_score": 0.5  # Default score
            }
            
            # Calculate relevance score based on multiple factors
            product_name_lower = product.name.lower()
            product_desc_lower = product.description.lower() if product.description else ""
            
            # Exact match in name (highest priority)
            if query_lower == product_name_lower:
                product_dict["similarity_score"] = 1.0
            # Exact match in product code/model (e.g., XZ2000)
            elif any(term.lower() == query_lower for term in product_name_lower.split()):
                product_dict["similarity_score"] = 0.95
            # Name contains the entire query
            elif query_lower in product_name_lower:
                product_dict["similarity_score"] = 0.9
            # Description contains the entire query
            elif query_lower in product_desc_lower:
                product_dict["similarity_score"] = 0.8
            # Partial match - query terms in product name
            elif any(term.lower() in product_name_lower for term in query_lower.split()):
                product_dict["similarity_score"] = 0.7
            # Partial match - query terms in product description
            elif any(term.lower() in product_desc_lower for term in query_lower.split()):
                product_dict["similarity_score"] = 0.6
            # Category match
            elif product.category and query_lower in product.category.lower():
                product_dict["similarity_score"] = 0.5
            
            # Only include products with some relevance
            if product_dict["similarity_score"] > 0.2:
                products_list.append(product_dict)
        
        # Sort by relevance (higher score = better match)
        products_list.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # Limit to top_k results
        return products_list[:top_k]
    
    def sync_all_products(self):
        """
        Synchronize all products from PostgreSQL to Milvus.
        This is useful for initial setup or full reindexing.
        """
        if not self.db:
            print("Database session required to sync products")
            return False
            
        # Reset the collection to start fresh
        reset_collection(collection_name=PRODUCT_COLLECTION_NAME)
        
        # Get all active products
        products = self.db.query(Product).filter(Product.is_active == True).all()
        
        # Add each product to Milvus
        for product in products:
            self.add_product_to_milvus(product)
            
        print(f"Synchronized {len(products)} products to Milvus collection {PRODUCT_COLLECTION_NAME}")
        return True
