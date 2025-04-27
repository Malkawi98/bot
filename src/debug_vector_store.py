#!/usr/bin/env python
"""
Debug script for the vector store.
This script will help diagnose issues with the Milvus vector database connection and data retrieval.
"""
import os
import sys
from pymilvus import connections, Collection, utility
from app.services.milvus_client import COLLECTION_NAME, MILVUS_HOST, MILVUS_PORT
from app.core.config import settings

def debug_milvus_connection():
    """Test the connection to Milvus and print debug information."""
    print("=== Milvus Connection Debug ===")
    
    # Get connection parameters
    host = os.getenv("MILVUS_HOST") or getattr(settings, "MILVUS_HOST", None) or MILVUS_HOST
    port = os.getenv("MILVUS_PORT") or getattr(settings, "MILVUS_PORT", None) or MILVUS_PORT
    api_key = os.getenv("MILVUS_API_KEY") or getattr(settings, "MILVUS_API_KEY", "")
    uri = os.getenv("MILVUS_URI") or getattr(settings, "MILVUS_URI", None)
    
    print(f"Connection parameters:")
    print(f"  URI: {uri}")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  API Key: {'Set' if api_key else 'Not set'}")
    
    # Try to connect
    try:
        if uri:
            print(f"Connecting using URI: {uri}")
            connections.connect("default", uri=uri, token=api_key, secure=not uri.startswith("http://"))
        else:
            print(f"Connecting using Host/Port: {host}:{port}")
            connections.connect("default", host=host, port=port, token=api_key)
        
        print("✅ Successfully connected to Milvus")
    except Exception as e:
        print(f"❌ Failed to connect to Milvus: {e}")
        return False
    
    return True

def list_collections():
    """List all collections in Milvus."""
    print("\n=== Milvus Collections ===")
    try:
        collections = utility.list_collections()
        print(f"Available collections: {collections}")
        
        if not collections:
            print("❌ No collections found in Milvus")
            return []
        
        return collections
    except Exception as e:
        print(f"❌ Error listing collections: {e}")
        return []

def inspect_collection(collection_name):
    """Inspect a specific collection."""
    print(f"\n=== Inspecting Collection: {collection_name} ===")
    try:
        col = Collection(collection_name)
        print(f"Collection name: {col.name}")
        print(f"Description: {col.description}")
        
        # Get schema
        schema = col.schema
        print(f"Schema fields: {[field.name for field in schema.fields]}")
        
        # Get entity count
        num_entities = col.num_entities
        print(f"Number of entities: {num_entities}")
        
        # Get index info
        try:
            index_info = col.index().info
            print(f"Index info: {index_info}")
        except Exception as e:
            print(f"❌ Error getting index info: {e}")
        
        return num_entities > 0
    except Exception as e:
        print(f"❌ Error inspecting collection: {e}")
        return False

def query_collection(collection_name):
    """Query all entries in a collection."""
    print(f"\n=== Querying Collection: {collection_name} ===")
    try:
        col = Collection(collection_name)
        
        # Load collection into memory
        col.load()
        
        # Try different query approaches
        print("Attempting to query with 'id > 0'...")
        try:
            results = col.query(
                expr="id > 0",
                output_fields=["id", "text", "language"],
                limit=10
            )
            print(f"Query results count: {len(results)}")
            if results:
                print("First few results:")
                for i, result in enumerate(results[:3]):
                    print(f"  {i+1}. ID: {result.get('id')}, Language: {result.get('language')}, Text: {result.get('text')[:50]}...")
            else:
                print("No results found with this query")
        except Exception as e:
            print(f"❌ Error with 'id > 0' query: {e}")
        
        # Try alternative query
        print("\nAttempting to query all entries...")
        try:
            results = col.query(
                expr="",  # Empty expression to match all
                output_fields=["id", "text", "language"],
                limit=10
            )
            print(f"Query results count: {len(results)}")
            if results:
                print("First few results:")
                for i, result in enumerate(results[:3]):
                    print(f"  {i+1}. ID: {result.get('id')}, Language: {result.get('language')}, Text: {result.get('text')[:50]}...")
            else:
                print("No results found with this query")
        except Exception as e:
            print(f"❌ Error with empty query: {e}")
        
        return True
    except Exception as e:
        print(f"❌ Error querying collection: {e}")
        return False

def fix_vector_store_api():
    """Suggest fixes for the vector store API."""
    print("\n=== Recommended Fixes ===")
    print("Based on the diagnostics, here are recommended fixes:")
    
    print("1. Update get_all_entries function in milvus_client.py:")
    print("   - Try alternative query expressions")
    print("   - Add more detailed error logging")
    print("   - Ensure proper collection loading before query")
    
    print("2. Check collection name consistency:")
    print("   - Ensure the same collection name is used everywhere")
    print("   - Verify collection exists before querying")
    
    print("3. Verify database connection parameters:")
    print("   - Check if environment variables are correctly set")
    print("   - Ensure URI or host/port are properly configured")

def main():
    """Main function to run all diagnostics."""
    print("Starting Vector Store Diagnostics")
    print("=" * 50)
    
    # Test connection
    if not debug_milvus_connection():
        print("\n❌ Connection failed. Please fix connection issues before continuing.")
        return
    
    # List collections
    collections = list_collections()
    if not collections:
        print("\n❌ No collections found. Please create a collection and add data.")
        return
    
    # Check if our target collection exists
    if COLLECTION_NAME in collections:
        print(f"\n✅ Target collection '{COLLECTION_NAME}' found.")
        
        # Inspect the collection
        has_entities = inspect_collection(COLLECTION_NAME)
        if has_entities:
            print(f"\n✅ Collection '{COLLECTION_NAME}' has entities.")
            
            # Query the collection
            query_collection(COLLECTION_NAME)
        else:
            print(f"\n❌ Collection '{COLLECTION_NAME}' exists but has no entities.")
    else:
        print(f"\n❌ Target collection '{COLLECTION_NAME}' not found.")
        
        # Inspect the first available collection as an alternative
        alt_collection = collections[0]
        print(f"Inspecting alternative collection: {alt_collection}")
        inspect_collection(alt_collection)
        query_collection(alt_collection)
    
    # Suggest fixes
    fix_vector_store_api()
    
    print("\nDiagnostics complete.")

if __name__ == "__main__":
    main()
