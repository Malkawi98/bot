from sqlalchemy.orm import Session
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate
from typing import List, Optional
from datetime import datetime
from app.services.rag import RAGService
from app.services.product_embedding import ProductEmbeddingService


class ProductService:
    """Service for managing products in the database and vector store."""
    
    def __init__(self, db: Session):
        self.db = db
        self.rag_service = RAGService()
        self.embedding_service = ProductEmbeddingService(db)
    
    def get_product(self, product_id: int) -> Optional[Product]:
        """Get a product by ID."""
        return self.db.query(Product).filter(Product.id == product_id).first()
    
    def get_products(self, skip: int = 0, limit: int = 100, category: Optional[str] = None, 
                    language: Optional[str] = None, is_active: bool = True) -> List[Product]:
        """Get a list of products with optional filtering."""
        query = self.db.query(Product).filter(Product.is_active == is_active)
        
        if category:
            query = query.filter(Product.category == category)
        
        if language:
            query = query.filter(Product.language == language)
        
        return query.offset(skip).limit(limit).all()
    
    def create_product(self, product: ProductCreate) -> Product:
        """Create a new product and add it to the vector store."""
        # Create a new Product instance without using constructor arguments
        db_product = Product()
        
        # Set attributes manually
        db_product.name = product.name
        db_product.description = product.description
        db_product.price = product.price
        db_product.currency = product.currency
        db_product.stock_quantity = product.stock_quantity
        db_product.image_url = product.image_url
        db_product.category = product.category
        db_product.language = product.language
        db_product.alternative_to_id = product.alternative_to_id
        db_product.created_at = datetime.now().isoformat()
        db_product.updated_at = datetime.now().isoformat()
        
        self.db.add(db_product)
        self.db.commit()
        self.db.refresh(db_product)
        
        # Add product to both RAG and dedicated product vector store
        self._add_to_vector_store(db_product)
        self.embedding_service.add_product_to_milvus(db_product)
        
        return db_product
    
    def update_product(self, product_id: int, product_update: ProductUpdate) -> Optional[Product]:
        """Update an existing product."""
        db_product = self.get_product(product_id)
        if not db_product:
            return None
        
        # Update only the fields that are provided
        update_data = product_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_product, key, value)
        
        # Always update the updated_at timestamp
        db_product.updated_at = datetime.now().isoformat()
        
        self.db.commit()
        self.db.refresh(db_product)
        
        # Update product in both RAG and dedicated product vector store
        self._add_to_vector_store(db_product)
        self.embedding_service.add_product_to_milvus(db_product)
        
        return db_product
    
    def delete_product(self, product_id: int) -> bool:
        """Soft delete a product by setting is_active to False."""
        db_product = self.get_product(product_id)
        if not db_product:
            return False
        
        db_product.is_active = False
        db_product.updated_at = datetime.now().isoformat()
        
        self.db.commit()
        
        # We don't remove from RAG vector store, just update to show as inactive
        self._add_to_vector_store(db_product)
        
        # Remove from the dedicated product vector store
        self.embedding_service.remove_product_from_milvus(product_id)
        
        return True
    
    def get_product_count(self, category: Optional[str] = None, language: Optional[str] = None) -> int:
        """Get the total count of products with optional filtering."""
        query = self.db.query(Product).filter(Product.is_active == True)
        
        if category:
            query = query.filter(Product.category == category)
        
        if language:
            query = query.filter(Product.language == language)
        
        return query.count()
    
    def get_product_alternatives(self, product_id: int) -> List[Product]:
        """Get alternative products for a given product."""
        return self.db.query(Product).filter(
            Product.alternative_to_id == product_id,
            Product.is_active == True
        ).all()
        
    def get_products_by_ids(self, product_ids: List[int]) -> List[Product]:
        """Get products by their IDs.
        
        This method is used to fetch products after searching for them in the vector store.
        
        Args:
            product_ids: List of product IDs to fetch
            
        Returns:
            List of Product objects
        """
        if not product_ids:
            return []
            
        return self.db.query(Product).filter(
            Product.id.in_(product_ids),
            Product.is_active == True
        ).all()
        
    def find_similar_products(self, product_name: str, language: str = None, limit: int = 3) -> List[Product]:
        """Find similar products based on name similarity or category"""
        # First try to find products with similar names
        query = self.db.query(Product).filter(Product.is_active == True)
        
        # If language is specified, filter by language
        if language:
            query = query.filter(Product.language == language)
            
        # Get all products to perform similarity matching
        all_products = query.all()
        
        # If no products found, return empty list
        if not all_products:
            return []
            
        # Calculate similarity scores based on product name
        # This is a simple implementation using string similarity
        # For production, consider using more advanced NLP techniques
        from difflib import SequenceMatcher
        
        def similarity_score(a, b):
            return SequenceMatcher(None, a.lower(), b.lower()).ratio()
        
        # Calculate similarity for each product
        scored_products = [
            (product, similarity_score(product.name, product_name))
            for product in all_products
        ]
        
        # Sort by similarity score (highest first)
        scored_products.sort(key=lambda x: x[1], reverse=True)
        
        # Return the top N similar products
        similar_products = [product for product, score in scored_products[:limit] if score > 0.3]
        
        # If we couldn't find similar products by name, try to find products in the same category
        if not similar_products and len(all_products) > 0:
            # Try to extract category from the product name
            # This is a simplified approach - in production, use NLP for better category extraction
            possible_categories = [p.category for p in all_products if p.category]
            
            # Find products from the most common categories
            if possible_categories:
                from collections import Counter
                category_counts = Counter(possible_categories)
                top_categories = [cat for cat, count in category_counts.most_common(2)]
                
                category_products = query.filter(Product.category.in_(top_categories)).limit(limit).all()
                if category_products:
                    return category_products
        
        return similar_products
    
    def _add_to_vector_store(self, product: Product):
        """Add product details to the vector store for RAG."""
        # Create a detailed text representation of the product
        product_text = f"""
Product: {product.name}
ID: {product.id}
Category: {product.category or 'Uncategorized'}
Price: {product.price} {product.currency}
In Stock: {'Yes' if product.stock_quantity > 0 else 'No'}
Stock Quantity: {product.stock_quantity} items
Status: {'Active' if product.is_active else 'Inactive'}
Description: {product.description or 'No description available'}
"""
        
        # Add to vector store with the product's language
        self.rag_service.add_text_to_milvus(product_text, language=product.language)
