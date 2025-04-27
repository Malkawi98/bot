from langchain_core.tools import tool
from app.services.rag import RAGService
from typing import List, Dict, Any, Optional
import re
import random
from datetime import datetime, timedelta
from app.services.graph_service.state import ConversationState
from app.services.product_search import ProductSearchService
from app.services.product import ProductService
from sqlalchemy.orm import Session

# Initialize Services
rag_service = RAGService()

# Mock data for demonstration (only used as fallback)
ORDER_STATUSES = ["Processing", "Shipped", "Delivered", "Cancelled"]
# We'll replace this with actual database queries
FALLBACK_PRODUCTS = [
    {"id": 1, "name": "Wireless Earbuds", "price": 79.99, "stock": 15},
    {"id": 2, "name": "Smart Watch", "price": 199.99, "stock": 8},
    {"id": 3, "name": "Bluetooth Speaker", "price": 59.99, "stock": 0},
    {"id": 4, "name": "Laptop Backpack", "price": 49.99, "stock": 23},
    {"id": 5, "name": "Phone Charger", "price": 19.99, "stock": 42}
]

def _generate_random_order_number():
    return str(random.randint(10000, 99999))

def _get_product_info(product_name, db: Optional[Session] = None):
    """Get product information from the database or fallback to mock data"""
    if db is None:
        # Fallback to mock data if no database session
        print("No database session provided, using fallback product data")
        product_name = product_name.lower()
        for product in FALLBACK_PRODUCTS:
            if product_name in product["name"].lower():
                return product
        return None
    
    # Use the ProductSearchService to search the database
    try:
        product_search = ProductSearchService(db)
        found, product_info = product_search.search_product_by_name(product_name)
        if found:
            # Convert database product to the expected format
            return {
                "id": product_info["id"],
                "name": product_info["name"],
                "price": product_info["price"],
                "stock": product_info["stock_quantity"],
                "description": product_info.get("description", ""),
                "category": product_info.get("category", "")
            }
        return None
    except Exception as e:
        print(f"Error searching for product: {e}")
        return None

def _get_order_info(order_number):
    # Mock order information
    status = random.choice(ORDER_STATUSES)
    order_date = datetime.now() - timedelta(days=random.randint(1, 14))
    estimated_delivery = order_date + timedelta(days=random.randint(3, 10))
    
    order_info = {
        "order_id": order_number,
        "status": status,
        "order_date": order_date.strftime("%Y-%m-%d"),
        "estimated_delivery": estimated_delivery.strftime("%Y-%m-%d") if status != "Delivered" else None,
        "delivery_date": (order_date + timedelta(days=random.randint(2, 7))).strftime("%Y-%m-%d") if status == "Delivered" else None,
        "items": [random.choice(PRODUCTS) for _ in range(random.randint(1, 3))],
        "total": round(random.uniform(20, 500), 2)
    }
    
    # Generate reply text based on status
    if status == "Processing":
        reply_text = f"Your order #{order_number} is currently being processed. It was placed on {order_info['order_date']} and should be shipped soon. The estimated delivery date is {order_info['estimated_delivery']}."
    elif status == "Shipped":
        reply_text = f"Good news! Your order #{order_number} has been shipped. It was placed on {order_info['order_date']} and should be delivered by {order_info['estimated_delivery']}."
    elif status == "Delivered":
        reply_text = f"Your order #{order_number} has been delivered on {order_info['delivery_date']}. It was placed on {order_info['order_date']}. We hope you're enjoying your purchase!"
    else:  # Cancelled
        reply_text = f"I'm sorry, but your order #{order_number} has been cancelled. It was placed on {order_info['order_date']}. If you didn't request this cancellation, please contact our customer support."
    
    return order_info, reply_text

@tool("knowledge_base_retriever")
def retrieve_from_kb(query: str) -> str:
    """Searches the knowledge base for information related to the user query."""
    print(f"--- Tool: Retrieving KB context for: {query} ---")
    
    # First attempt: Use RAG service directly
    try:
        from app.services.rag import RAGService
        rag_service = RAGService()
        search_results = rag_service.search_similar(query, top_k=2)
        
        texts = []
        if isinstance(search_results, list):
            for result in search_results:
                if isinstance(result, dict) and "text" in result:
                    texts.append(result["text"])
                    print(f"--- Tool: Found text result via RAG service ---")
        
        if texts:
            context = "\n\n".join(texts)
            print(f"--- Tool: Found KB context via RAG service: {len(context)} characters ---")
            return context
    except Exception as e:
        print(f"--- Tool: Error with RAG service: {e} ---")
    
    # Second attempt: Use Milvus client directly
    try:
        from app.services.milvus_client import get_collection, search_embedding
        from app.services.embeddings import get_embedder

        # Get embeddings for the query
        embedder = get_embedder()
        embedding = embedder.embed(query)
        
        # Search directly in Milvus
        search_results = search_embedding(embedding, top_k=2)
        
        texts = []
        if isinstance(search_results, list):
            for result in search_results:
                if isinstance(result, dict) and "text" in result:
                    texts.append(result["text"])
                    print(f"--- Tool: Found text result via direct Milvus search ---")
        
        if texts:
            context = "\n\n".join(texts)
            print(f"--- Tool: Found KB context via direct Milvus search: {len(context)} characters ---")
            return context
    except Exception as e:
        print(f"--- Tool: Error with direct Milvus search: {e} ---")
    
    # Third attempt: Use keyword matching with Milvus collection data
    try:
        from app.services.milvus_client import list_collections, load_collection
        
        # Get all entries from Milvus collection
        collection_name = "rag_embeddings"  # Default collection name
        if collection_name in list_collections():
            col = load_collection(collection_name)
            # Query all entries
            results = col.query(expr="id > 0", output_fields=["text", "id"])
            
            # Filter by keyword matching
            texts = []
            for result in results:
                text = result.get("text", "")
                if any(keyword.lower() in text.lower() for keyword in query.lower().split()):
                    texts.append(text)
                    print(f"--- Tool: Found keyword match in Milvus collection ---")
            
            if texts:
                context = "\n\n".join(texts)
                print(f"--- Tool: Found KB context via keyword matching: {len(context)} characters ---")
                return context
    except Exception as e:
        print(f"--- Tool: Error with Milvus keyword matching: {e} ---")
    
    # If all attempts fail, return a message indicating no information was found
    print("--- Tool: No text results found. ---")
    return "No relevant information found in the knowledge base."

@tool("order_status_checker")
def get_order_status(order_id_or_query: str) -> Dict[str, Any]:
    """
    Checks the status of an e-commerce order.
    Input can be an order ID or a query like 'where is my order?'.
    """
    print(f"--- Tool: Checking order status for: {order_id_or_query} ---")
    # Accept only order IDs 1-5
    order_id_match = re.search(r"order\s*(\d+)" , order_id_or_query, re.IGNORECASE)
    order_id = int(order_id_match.group(1)) if order_id_match else None

    if order_id is not None:
        if 1 <= order_id <= 5:
            # For demo, generate a 5-digit order number based on the ID
            order_number = f"1000{order_id}"
        else:
            return {"error": "Order ID not found. Please provide a valid order ID (1-5)."}
    else:
        return {"error": "Please provide a valid order ID (1-5) to check your order status."}

    try:
        # Get order info
        order_info, _ = _get_order_info(order_number)
        print(f"--- Tool: Order info found: {order_info} ---")
        return order_info
    except Exception as e:
        print(f"--- Tool: Error checking order status: {e} ---")
        return {"error": "Could not retrieve order status.", "order_id": order_number}

@tool("product_availability_checker")
def check_product_availability(product_name: str) -> Dict[str, Any]:
    """Checks if a product is in stock."""
    print(f"--- Tool: Checking availability for: {product_name} ---")
    # We can't pass the db directly through the tool due to Pydantic schema limitations
    # The db will be handled in the node function instead
    db = None
    
    # Extract product name from query if a full query was passed
    if len(product_name.split()) > 3:  # Likely a full query, not just a product name
        product_match = re.search(r'(?:do you have|is there|availability of|stock of|looking for)\s+([\w\s]+)(?:\?|$)', product_name.lower())
        if not product_match:
            # Try a more general pattern
            product_match = re.search(r'([\w\s]+)(?:\s+in stock|\s+available|\?|$)', product_name.lower())
        
        if product_match:
            product_name = product_match.group(1).strip()
            print(f"--- Tool: Extracted product name: {product_name} ---")
    
    # Look in database products
    product = _get_product_info(product_name, db)
    if product:
        # For database products, stock is stored as stock_quantity
        stock_field = "stock" if "stock" in product else "stock_quantity"
        availability = "In Stock" if product.get(stock_field, 0) > 0 else "Out of Stock"
        stock_count = product.get(stock_field, 0)
        print(f"--- Tool: Product '{product['name']}' availability: {availability} ({stock_count}) ---")
        return {
            "product_name": product['name'],
            "availability": availability,
            "stock": stock_count,
            "price": product.get('price', 0),
            "description": product.get('description', ''),
            "category": product.get('category', '')
        }
    else:
        print(f"--- Tool: Product '{product_name}' not found. ---")
        return {"product_name": product_name, "availability": "Not Found", "error": "Product not found in catalog."}

# Combine tools for the graph
tools = [retrieve_from_kb, get_order_status, check_product_availability]
