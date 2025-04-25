from langchain_core.tools import tool
from app.services.rag import RAGService
from typing import List, Dict, Any, Optional
import re
import random
from datetime import datetime, timedelta
from app.services.graph_service.state import ConversationState

# Initialize Services
rag_service = RAGService()

# Mock data for demonstration
ORDER_STATUSES = ["Processing", "Shipped", "Delivered", "Cancelled"]
PRODUCTS = [
    {"id": 1, "name": "Wireless Earbuds", "price": 79.99, "stock": 15},
    {"id": 2, "name": "Smart Watch", "price": 199.99, "stock": 8},
    {"id": 3, "name": "Bluetooth Speaker", "price": 59.99, "stock": 0},
    {"id": 4, "name": "Laptop Backpack", "price": 49.99, "stock": 23},
    {"id": 5, "name": "Phone Charger", "price": 19.99, "stock": 42}
]

def _generate_random_order_number():
    return str(random.randint(10000, 99999))

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
    order_number_match = re.search(r"\d{5,}", order_id_or_query) # Simple regex for demo
    order_number = order_number_match.group(0) if order_number_match else None

    if not order_number:
        # If no order number found, generate a mock one for demo
        order_number = _generate_random_order_number()
        print(f"--- Tool: No order ID found, using mock ID: {order_number} ---")

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
    # Look in PRODUCTS
    found = [p for p in PRODUCTS if product_name.lower() in p['name'].lower()]
    if found:
        product = found[0]
        availability = "In Stock" if product.get("stock", 0) > 0 else "Out of Stock"
        stock_count = product.get("stock", 0)
        print(f"--- Tool: Product '{product['name']}' availability: {availability} ({stock_count}) ---")
        return {"product_name": product['name'], "availability": availability, "stock": stock_count}
    else:
        print(f"--- Tool: Product '{product_name}' not found. ---")
        return {"product_name": product_name, "availability": "Not Found", "error": "Product not found in catalog."}

# Combine tools for the graph
tools = [retrieve_from_kb, get_order_status, check_product_availability]
