from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
from pymilvus import utility
import os
import openai

from app.core.config import settings

MILVUS_HOST = "localhost"  # Use localhost for local development
MILVUS_PORT = "19530"

COLLECTION_NAME = "rag_embeddings"
EMBEDDING_DIM = 3072  # text-embedding-3-large has 3072 dimensions
EMBEDDING_MODEL = "text-embedding-3-large"  # Updated to better multilingual model

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY") or getattr(settings, "OPENAI_API_KEY", "")


def connect_to_milvus(alias: str = "default"):
    """
    Connect to Milvus using host/port from environment or settings.
    """
    from pymilvus import connections

    # Prefer MILVUS_HOST and MILVUS_PORT env vars, fallback to settings.MILVUS_URI
    host = os.getenv("MILVUS_HOST") or getattr(settings, "MILVUS_HOST", None) or MILVUS_HOST
    port = os.getenv("MILVUS_PORT") or getattr(settings, "MILVUS_PORT", None) or MILVUS_PORT
    api_key = os.getenv("MILVUS_API_KEY") or getattr(settings, "MILVUS_API_KEY", "")
    # If URI is set in settings and not overridden by env, use it
    uri = os.getenv("MILVUS_URI") or getattr(settings, "MILVUS_URI", None)
    if uri:
        connection_args = {"uri": uri, "token": api_key, "secure": not uri.startswith("http://")}
    else:
        connection_args = {"host": host, "port": port, "token": api_key}
    try:
        connections.connect(alias=alias, **connection_args)
    except Exception as e:
        raise


def create_collection(collection_name: str = COLLECTION_NAME, dim: int = EMBEDDING_DIM):
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2048),
        # Add language field for multilingual support
        FieldSchema(name="language", dtype=DataType.VARCHAR, max_length=10),
    ]
    schema = CollectionSchema(fields, description="Multilingual RAG text embeddings")
    
    # Create collection if it doesn't exist
    if collection_name not in list_collections():
        Collection(name=collection_name, schema=schema)
        print(f"Created new collection: {collection_name}")
    
    collection = Collection(collection_name)
    
    # Create index if it doesn't exist
    try:
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {"nlist": 128}
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        print(f"Created index on collection: {collection_name}")
    except Exception as e:
        if "index already exists" in str(e).lower():
            print(f"Index already exists on collection: {collection_name}")
        else:
            print(f"Error creating index: {e}")
    
    # Load collection
    try:
        collection.load()
        print(f"Loaded collection: {collection_name}")
    except Exception as e:
        print(f"Error loading collection: {e}")
    
    return collection


def list_collections():
    return utility.list_collections()


def drop_collection(collection_name: str = COLLECTION_NAME):
    """
    Drop the Milvus collection if it exists.
    """
    from pymilvus import utility
    if collection_name in utility.list_collections():
        utility.drop_collection(collection_name)
        
def reset_collection(collection_name: str = COLLECTION_NAME):
    """
    Reset the Milvus collection by dropping it and recreating it.
    This effectively clears all embeddings.
    """
    try:
        # Drop the collection if it exists
        drop_collection(collection_name)
        print(f"Dropped collection: {collection_name}")
        
        # Create a new collection with the same schema
        collection = create_collection(collection_name)
        
        # Make sure the index is created
        try:
            index_params = {
                "index_type": "IVF_FLAT",
                "metric_type": "L2",
                "params": {"nlist": 128}
            }
            collection.create_index(field_name="embedding", index_params=index_params)
            print(f"Created index on collection: {collection_name}")
        except Exception as e:
            print(f"Error creating index during reset: {e}")
        
        # Load the collection
        collection.load()
        print(f"Collection {collection_name} has been reset and loaded")
        return True
    except Exception as e:
        print(f"Error resetting collection: {e}")
        raise e


def build_index(collection_name: str = COLLECTION_NAME):
    """Build an index on the embedding field for faster search"""
    if collection_name not in list_collections():
        return

    col = Collection(collection_name)
    # Check if index already exists
    has_index = False
    try:
        index_info = col.index().params
        has_index = True
    except Exception:
        has_index = False

    if not has_index:
        # Create index on the embedding field
        index_params = {"metric_type": "L2", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
        col.create_index("embedding", index_params)
    return col


def load_collection(collection_name: str = COLLECTION_NAME):
    """Load the collection into memory for search"""
    if collection_name not in list_collections():
        create_collection(collection_name)

    col = Collection(collection_name)
    col.load()
    return col


def insert_embedding(embedding: list[float], text: str, collection_name: str = COLLECTION_NAME, language: str = "en"):
    """
    Insert a single embedding and its corresponding text into the collection.
    This function is optimized for single item insertion.
    
    Args:
        embedding: The embedding vector
        text: The text content
        collection_name: Name of the collection
        language: Language code (e.g., 'en', 'ar')
    """
    try:
        # Connect to Milvus
        connect_to_milvus()
        
        # Ensure collection exists
        if collection_name not in list_collections():
            create_collection(collection_name)
        
        # Get collection
        collection = Collection(collection_name)
        
        # Insert data with language metadata
        # Format data correctly for Milvus insertion
        # The expected format is a list of entities, where each entity is a dict of field values
        entities = [
            {
                "embedding": embedding,  # embedding field - single vector
                "text": text,           # text field - single string
                "language": language     # language field - single string
            }
        ]
        
        # Debug output
        print(f"Inserting entity with embedding length: {len(embedding)}, text length: {len(text)}, language: {language}")
        
        # Insert the entities
        collection.insert(entities)
        return True
    except Exception as e:
        print(f"Error inserting embedding: {e}")
        return False


def insert_embeddings(embeddings: list[list[float]], texts: list[str],
                      collection_name: str = COLLECTION_NAME, languages: list[str] = None):
    """
    Insert multiple embeddings and their corresponding texts into the collection.
    This function is for batch insertion of multiple items.
    
    Args:
        embeddings: List of embedding vectors
        texts: List of text content
        collection_name: Name of the collection
        languages: List of language codes (e.g., ['en', 'ar']). If None, defaults to 'en' for all.
    """
    if not embeddings or not texts or len(embeddings) != len(texts):
        print("Error: embeddings and texts must be non-empty lists of the same length")
        return False
    
    # Default to English if languages not provided
    if not languages:
        languages = ['en'] * len(texts)
    elif len(languages) != len(texts):
        print("Error: languages list must be the same length as texts")
        languages = ['en'] * len(texts)
    
    try:
        # Connect to Milvus
        connect_to_milvus()
        
        # Ensure collection exists
        if collection_name not in list_collections():
            create_collection(collection_name)
        
        # Get collection
        collection = Collection(collection_name)
        
        # Insert data with language metadata
        # Format data correctly for Milvus batch insertion
        # The expected format is a list of entities, where each entity is a dict of field values
        entities = []
        
        for i in range(len(embeddings)):
            entities.append({
                "embedding": embeddings[i],  # embedding field - vector
                "text": texts[i],           # text field - string
                "language": languages[i]     # language field - string
            })
        
        # Debug output
        print(f"Batch inserting {len(entities)} entities with embeddings")
        
        # Insert the entities
        collection.insert(entities)
        return True
    except Exception as e:
        print(f"Error inserting embeddings: {e}")
        return False


def insert_embeddings_with_metadata(embeddings: list[list[float]], texts: list[str],
                                  metadata: list[dict] = None,
                                  collection_name: str = COLLECTION_NAME):
    """
    Insert multiple embeddings with their texts and metadata into the collection.
    
    Args:
        embeddings: List of embedding vectors
        texts: List of text content
        metadata: List of metadata dictionaries, each containing at least a 'language' key
        collection_name: Name of the collection
    """
    if not embeddings or not texts or len(embeddings) != len(texts):
        print("Error: embeddings and texts must be non-empty lists of the same length")
        return False
    
    # Extract languages from metadata or default to English
    languages = []
    if metadata and len(metadata) == len(texts):
        for meta in metadata:
            languages.append(meta.get('language', 'en'))
    else:
        languages = ['en'] * len(texts)
    
    return insert_embeddings(embeddings, texts, collection_name, languages)


def get_embedding(text: str) -> list[float]:
    """
    Generate embeddings for a text using OpenAI's embedding model.
    """
    try:
        # Check if the OpenAI API key is set
        if not openai.api_key:
            # Use a mock embedding for testing if no API key is available
            return [0.0] * EMBEDDING_DIM

        # Get embeddings from OpenAI
        response = openai.Embedding.create(input=text, model=EMBEDDING_MODEL)

        # Extract the embedding from the response
        embedding = response["data"][0]["embedding"]
        return embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        # Return a mock embedding in case of error
        return [0.0] * EMBEDDING_DIM


def search_embedding(embedding: list[float], top_k: int = 5,
                     collection_name: str = COLLECTION_NAME,
                     filter_expr: str = None):
    # Ensure collection exists
    if collection_name not in list_collections():
        print(f"Collection {collection_name} does not exist. Creating it.")
        create_collection(collection_name)
        # If collection is empty, return empty results
        return []

    # Build index if needed
    build_index(collection_name)

    # Load collection into memory
    col = load_collection(collection_name)
    
    # Perform search
    try:
        print(f"Searching in collection {collection_name} with top_k={top_k}")
        results = col.search(
            data=[embedding], 
            anns_field="embedding",
            param={"metric_type": "L2", "params": {"nprobe": 10}}, 
            limit=top_k,
            output_fields=["text", "language"], 
        )
        print(f"Search results: {results}")
        
        # Direct approach - extract text from search results
        simplified_results = []
        
        # Handle the case where results might be a string representation
        if isinstance(results, str):
            print("Results are in string format, attempting to parse...")
            # This is a fallback for when results are returned as a string
            import re
            # Extract text fields from the string representation
            text_matches = re.findall(r"text': '([^']+)'}", results)
            for text in text_matches:
                simplified_results.append({
                    'text': text,
                    'score': 0.0  # We don't have score info in this case
                })
                print(f"Extracted text from string: {text[:50]}...")
        else:
            # Normal case - results are objects
            if results and len(results) > 0:
                for hit in results[0]:
                    try:
                        if hasattr(hit, 'entity') and isinstance(hit.entity, dict):
                            text = hit.entity.get('text', '')
                            language = hit.entity.get('language', 'en')
                            if text:
                                simplified_results.append({
                                    'text': text,
                                    'language': language,
                                    'score': hit.distance if hasattr(hit, 'distance') else 0.0
                                })
                                print(f"Added text with score {hit.distance if hasattr(hit, 'distance') else 0.0}: {text[:50]}...")
                    except Exception as inner_e:
                        print(f"Error processing hit: {inner_e}")
        
        # If we still don't have results, try one more approach with the raw string
        if not simplified_results and isinstance(results, str):
            # Try to extract text directly from the string representation
            if "text" in results:
                # Very simple extraction - just get something useful
                start_idx = results.find("text") + 8  # Skip past "text': '"
                end_idx = results.find("'", start_idx)
                if start_idx > 8 and end_idx > start_idx:
                    text = results[start_idx:end_idx]
                    simplified_results.append({
                        'text': text,
                        'score': 0.0
                    })
                    print(f"Last resort extraction: {text[:50]}...")
        
        print(f"Simplified results: {len(simplified_results)} items")
        return simplified_results
    except Exception as e:
        import traceback
        print(f"Search error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        # Return empty results on error
        return []


def get_all_entries(collection_name: str = COLLECTION_NAME, limit: int = 1000):
    """
    Get all entries from the Milvus collection.
    
    Args:
        collection_name: Name of the collection to query
        limit: Maximum number of entries to return
        
    Returns:
        List of dictionaries containing the entries
    """
    # Print all available collections for debugging
    all_collections = list_collections()
    print(f"Available collections: {all_collections}")
    
    # Check if the collection exists in Milvus
    if collection_name not in all_collections:
        print(f"Warning: Collection '{collection_name}' not found in Milvus. Available collections: {all_collections}")
        # Try to find any collection that might contain embeddings
        if all_collections:
            alt_collection = all_collections[0]
            print(f"Trying alternative collection: {alt_collection}")
            return get_all_entries(alt_collection, limit)
        else:
            print("No collections found in Milvus")
            create_collection(collection_name)
            return []
    
    try:
        # Get collection and ensure it has an index
        col = Collection(collection_name)
        print(f"Opened collection: {collection_name}")
        
        # Print collection info
        try:
            schema = col.schema
            print(f"Collection schema: {schema}")
            num_entities = col.num_entities
            print(f"Collection has {num_entities} entities")
        except Exception as e:
            print(f"Error getting collection info: {e}")
        
        # Check if collection has an index
        try:
            index_info = col.index().info
            print(f"Index info: {index_info}")
            if not index_info:
                # Create index if it doesn't exist
                try:
                    index_params = {
                        "index_type": "IVF_FLAT",
                        "metric_type": "L2",
                        "params": {"nlist": 128}
                    }
                    col.create_index(field_name="embedding", index_params=index_params)
                    print(f"Created index on collection: {collection_name}")
                except Exception as e:
                    print(f"Error creating index: {e}")
        except Exception as e:
            print(f"Error checking index: {e}")
        
        # Load collection into memory
        col.load()
        
        # Query all entries - use the most reliable method based on our debug findings
        try:
            # Get the schema fields to determine what fields are available
            schema_fields = [field.name for field in col.schema.fields]
            print(f"Available schema fields: {schema_fields}")
            
            # Determine which output fields to use based on what's available in the schema
            output_fields = ["id", "text"]
            if "language" in schema_fields:
                output_fields.append("language")
            
            print(f"Using output fields: {output_fields}")
            
            # Use the standard query approach which we know works from our debug endpoint
            results = col.query(
                expr="id > 0",  # Query all entries
                output_fields=output_fields,
                limit=limit
            )
            
            if results and len(results) > 0:
                print(f"Retrieved {len(results)} entries using query")
                
                # Add default language if it's missing
                if "language" not in schema_fields:
                    for result in results:
                        result["language"] = "en"  # Add default language
                
                return results
            
            print("No results found with standard query")
            return []
        except Exception as e:
            print(f"Error querying entries: {e}")
            return []
    except Exception as e:
        print(f"Error getting all entries: {e}")
        # Return empty results on error
        return []
