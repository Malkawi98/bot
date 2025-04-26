"""
Product search service for the bot to find products in the database.
This replaces the mock product data with real database queries.
"""
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.product import Product
from app.services.product import ProductService
from app.services.product_embedding import ProductEmbeddingService
import difflib

class ProductSearchService:
    """Service for searching products in the database for the bot."""
    
    def __init__(self, db: Session):
        self.db = db
        self.product_service = ProductService(db)
        self.embedding_service = ProductEmbeddingService(db)
    
    def search_product_by_name(self, query: str, language: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Search for a product by name in the database and vector store.
        
        Args:
            query: The search query (product name)
            language: Optional language filter
            
        Returns:
            Tuple containing:
            - found: Whether a product was found
            - product_info: Product information if found, None otherwise
        """
        # Clean up the query
        query = query.lower().strip()
        
        # Detect language if not provided
        if not language:
            # Simple language detection based on characters
            arabic_chars = sum(1 for c in query if 0x0600 <= ord(c) <= 0x06FF)
            if arabic_chars > len(query) / 3:  # If more than 1/3 of chars are Arabic
                language = 'ar'
            else:
                language = 'en'
                
        print(f"--- Product search: query='{query}', detected language='{language}' ---")
        
        # First try database exact and partial matches for efficiency
        products = self.product_service.get_products(limit=100, language=language)
        
        if products:
            # Try exact match
            for product in products:
                if query == product.name.lower():
                    return True, self._format_product_to_dict(product)
            
            # Try partial match
            for product in products:
                if query in product.name.lower():
                    return True, self._format_product_to_dict(product)
                    
            # Special handling for common Arabic product queries
            if language == 'ar':
                # Map common Arabic product terms to English equivalents
                arabic_to_english = {
                    'قميص قطني': 'cotton shirt',
                    'قميص': 'shirt',
                    'قطني': 'cotton'
                }
                
                # Check if we have a mapping for this query
                english_query = arabic_to_english.get(query)
                if english_query:
                    print(f"--- Translating Arabic query '{query}' to English '{english_query}' ---")
                    # Search with the English equivalent
                    for product in products:
                        if english_query in product.name.lower():
                            return True, self._format_product_to_dict(product)
        
        # If no direct matches, use vector search for semantic matching
        try:
            # Search in the vector database
            vector_results = self.embedding_service.search_products(
                query=query,
                top_k=1,  # Get the best match
                language=language
            )
            
            if vector_results and len(vector_results) > 0:
                # Get the top result
                top_result = vector_results[0]
                
                # Get the full product from the database to ensure we have the latest data
                product_id = top_result.get("product_id")
                if product_id:
                    product = self.product_service.get_product(product_id)
                    if product and product.is_active:
                        return True, self._format_product_to_dict(product)
        except Exception as e:
            print(f"Vector search error: {e}")
            # Fall back to fuzzy matching if vector search fails
            pass
        
        # As a last resort, try fuzzy matching
        if products:
            product_names = [(p, p.name.lower()) for p in products]
            matches = difflib.get_close_matches(query, [name for _, name in product_names], n=1, cutoff=0.6)
            
            if matches:
                match = matches[0]
                # Find the product with this name
                for product, name in product_names:
                    if name == match:
                        return True, self._format_product_to_dict(product)
        
        return False, None
    
    def find_similar_products(self, product_name: str, language: Optional[str] = None, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Find similar products based on name or category using vector search.
        
        Args:
            product_name: The product name to find similar products for
            language: Optional language filter
            limit: Maximum number of similar products to return
            
        Returns:
            List of similar products
        """
        # Try vector search first for better semantic similarity
        try:
            vector_results = self.embedding_service.search_products(
                query=product_name,
                top_k=limit,
                language=language
            )
            
            if vector_results and len(vector_results) > 0:
                # Get the full products from the database
                product_ids = [result.get("product_id") for result in vector_results if result.get("product_id")]
                products = []
                
                for product_id in product_ids:
                    product = self.product_service.get_product(product_id)
                    if product and product.is_active:
                        products.append(product)
                
                if products:
                    return [self._format_product_to_dict(p) for p in products]
        except Exception as e:
            print(f"Vector search error for similar products: {e}")
            # Fall back to database search if vector search fails
            pass
        
        # Fall back to traditional database search
        similar_products = self.product_service.find_similar_products(product_name, language, limit)
        return [self._format_product_to_dict(p) for p in similar_products]
    
    def _format_product_to_dict(self, product: Product) -> Dict[str, Any]:
        """Convert a Product model to a dictionary for the bot response."""
        return {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "currency": product.currency,
            "description": product.description,
            "stock_quantity": product.stock_quantity,
            "category": product.category,
            "language": product.language,
            "in_stock": product.stock_quantity > 0,
            "image_url": product.image_url
        }
