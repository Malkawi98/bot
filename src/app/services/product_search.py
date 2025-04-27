"""
Product search service for the bot to find products in the database.
This replaces the mock product data with real database queries.
"""
from typing import List, Dict, Tuple, Any, Optional
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

        # Enhanced general search logic - no special handling for specific products
        # Perform a more thorough search in the database before falling back to vector search
        query_words = query.split()

        # Check if any product contains all the words in the query
        matching_products = []
        for product in products:
            product_name_lower = product.name.lower()
            # Check if all query words are in the product name
            if all(word in product_name_lower for word in query_words):
                matching_products.append(product)

        # If we found products containing all query words, return the first one
        if matching_products:
            print(f"--- Found product containing all query words: '{matching_products[0].name}' ---")
            return True, self._format_product_to_dict(matching_products[0])

        # If no product contains all words, look for products containing most words
        if query_words and len(query_words) > 1:
            best_match = None
            max_matches = 0

            for product in products:
                product_name_lower = product.name.lower()
                matches = sum(1 for word in query_words if word in product_name_lower)
                if matches > max_matches:
                    max_matches = matches
                    best_match = product

            # If we found a product matching most words (at least half), return it
            if best_match and max_matches >= len(query_words) / 2:
                print(f"--- Found product matching {max_matches}/{len(query_words)} query words: '{best_match.name}' ---")
                return True, self._format_product_to_dict(best_match)

        # Try fuzzy text matching as a fallback or additional search method
        # This is useful when vector search fails or returns poor results
        fuzzy_match = self._find_fuzzy_match(query, products)
        if fuzzy_match:
            print(f"--- Found fuzzy match: {fuzzy_match.name} ---")
            return True, self._format_product_to_dict(fuzzy_match)

        # If no direct or fuzzy matches, try vector search for semantic matching
        try:
            print(f"--- Attempting vector search for query: '{query}' ---")
            # Search in the vector database with more results to analyze
            # Handle potential schema differences based on the memory about vector store issues
            try:
                vector_results = self.embedding_service.search_products(
                    query=query,
                    top_k=3,  # Get top 3 matches to analyze
                    language=language
                )
            except Exception as schema_error:
                # If there's a schema error (like missing language field or dimension mismatch),
                # try without the language parameter
                if "language" in str(schema_error).lower() or "vector dimension mismatch" in str(schema_error).lower():
                    print(f"--- Vector search schema error: {schema_error}, retrying without language parameter ---")
                    vector_results = self.embedding_service.search_products(
                        query=query,
                        top_k=3  # Get top 3 matches to analyze
                    )
                else:
                    # Re-raise if it's not a schema-related error
                    raise

            if vector_results and len(vector_results) > 0:
                # Analyze all results to find the best match
                best_product = None
                best_score = 0

                for result in vector_results:
                    similarity_score = result.get("score", 0)
                    product_id = result.get("product_id")

                    if not product_id or similarity_score < 0.75:
                        continue  # Skip low similarity matches

                    print(f"--- Vector result: product_id={product_id}, score={similarity_score} ---")

                    # Get the full product from the database
                    product = self.product_service.get_product(product_id)
                    if not product or not product.is_active:
                        continue

                    # Calculate word overlap between query and product name
                    query_words = set(query.split())
                    product_words = set(product.name.lower().split())
                    word_overlap = query_words.intersection(product_words)
                    overlap_ratio = len(word_overlap) / max(len(query_words), 1)

                    # Calculate a combined score based on similarity and word overlap
                    combined_score = (similarity_score * 0.7) + (overlap_ratio * 0.3)

                    print(f"--- Product: {product.name}, similarity={similarity_score}, "
                          f"overlap={overlap_ratio}, combined={combined_score} ---")

                    if combined_score > best_score:
                        best_score = combined_score
                        best_product = product

                # Return the best product if it meets our threshold
                if best_product and best_score > 0.6:
                    print(f"--- Best product match: {best_product.name} with score {best_score} ---")
                    return True, self._format_product_to_dict(best_product)
        except Exception as e:
            if "vector dimension mismatch" in str(e).lower():
                print(f"Vector search error (dimension mismatch): {e}. Falling back to text-based search.")
            elif "language" in str(e).lower():
                print(f"Vector search error (language field issue): {e}. Falling back to text-based search.")
            else:
                print(f"Vector search error: {e}. Falling back to text-based search.")
            # Log the error but continue with the search process
            # We'll rely on text-based search methods instead

        # If we get here, it means we didn't find a match
        # So we should return False to indicate no product was found
        return False, None

    def _find_fuzzy_match(self, query: str, products: List[Product]) -> Optional[Product]:
        """Find the best fuzzy match for a query among products using difflib."""
        if not products or not query:
            return None

        # Normalize query
        query = query.lower().strip()
        query_words = set(query.split())

        # Calculate fuzzy match scores for each product
        best_match = None
        best_score = 0

        for product in products:
            product_name = product.name.lower()

            # Calculate sequence matcher ratio (similar to Levenshtein ratio)
            # This measures overall string similarity
            name_ratio = difflib.SequenceMatcher(None, query, product_name).ratio()

            # Calculate word overlap
            product_words = set(product_name.split())
            word_overlap = query_words.intersection(product_words)
            overlap_ratio = len(word_overlap) / max(len(query_words), 1) if query_words else 0

            # Check for substring match (partial match)
            partial_ratio = 0
            if query in product_name:
                partial_ratio = len(query) / len(product_name)

            # Combine scores with appropriate weights
            combined_score = (name_ratio * 0.4) + (overlap_ratio * 0.4) + (partial_ratio * 0.2)

            print(f"--- Fuzzy match: {product.name}, score={combined_score:.2f} ---")

            if combined_score > best_score:
                best_score = combined_score
                best_match = product

        # Only return matches above a certain threshold
        if best_match and best_score > 0.5:
            return best_match
        return None

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
            # Handle potential schema differences based on the memory about vector store issues
            try:
                vector_results = self.embedding_service.search_products(
                    query=product_name,
                    top_k=limit,
                    language=language
                )
            except Exception as schema_error:
                # If there's a schema error (like missing language field or dimension mismatch),
                # try without the language parameter
                if "language" in str(schema_error).lower() or "vector dimension mismatch" in str(schema_error).lower():
                    print(f"--- Vector search schema error: {schema_error}, retrying without language parameter ---")
                    vector_results = self.embedding_service.search_products(
                        query=product_name,
                        top_k=limit
                    )
                else:
                    # Re-raise if it's not a schema-related error
                    raise

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
