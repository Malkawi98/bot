#!/usr/bin/env python
"""
Test script for the bot's ability to find products when asked about them.
This script simulates user queries to the bot about products.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from app.core.db.database import sync_session
from app.services.product_search import ProductSearchService

def test_bot_product_queries():
    """Test the bot's ability to find products when asked about them."""
    db = sync_session()
    try:
        # Initialize the product search service
        product_search = ProductSearchService(db)
        
        # Test English product queries
        print("\n=== Testing English Product Queries ===")
        english_queries = [
            "Do you have any gaming laptops?",
            "I'm looking for a laptop with RTX graphics",
            "Is the XZ2000 laptop available?",
            "Do you have laptops with 32GB RAM?",
            "What's the price of the Gaming Laptop XZ2000?"
        ]
        
        for query in english_queries:
            print(f"\nUser Query: '{query}'")
            # First check if the product search service can find the product
            found, product_info = product_search.search_product_by_name(query, language="en")
            
            if found:
                print(f"Product Search Found: {product_info['name']} - {product_info.get('description', '')[:50]}...")
                print(f"Price: {product_info.get('price')} {product_info.get('currency')}")
                print(f"Stock: {product_info.get('stock_quantity')} units")
            else:
                print("Product Search: No product found")
            
            # We don't have a direct bot response service, so we'll skip this part
            print("Bot response testing skipped - would be handled by the chat UI")
        
        # Test Arabic product queries
        print("\n=== Testing Arabic Product Queries ===")
        arabic_queries = [
            "هل لديكم لابتوب ألعاب؟",
            "أبحث عن لابتوب بمعالج رسومات قوي",
            "هل لابتوب XZ2000 متوفر؟",
            "ما هو سعر لابتوب الألعاب XZ2000؟",
            "كم سعر لابتوب XZ2000؟"
        ]
        
        for query in arabic_queries:
            print(f"\nUser Query: '{query}'")
            # First check if the product search service can find the product
            found, product_info = product_search.search_product_by_name(query, language="ar")
            
            if found:
                print(f"Product Search Found: {product_info['name']} - {product_info.get('description', '')[:50]}...")
                print(f"Price: {product_info.get('price')} {product_info.get('currency')}")
                print(f"Stock: {product_info.get('stock_quantity')} units")
            else:
                print("Product Search: No product found")
            
            # We don't have a direct bot response service, so we'll skip this part
            print("Bot response testing skipped - would be handled by the chat UI")
                
    finally:
        db.close()

if __name__ == "__main__":
    test_bot_product_queries()
