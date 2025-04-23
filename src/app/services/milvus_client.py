from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
from pymilvus import utility
import os
import openai

from app.core.config import settings

MILVUS_HOST = "milvus"  # Docker service name from docker-compose
MILVUS_PORT = "19530"

COLLECTION_NAME = "rag_embeddings"
EMBEDDING_DIM = 1536  # Adjust to your embedding model's output size
EMBEDDING_MODEL = "text-embedding-ada-002"  # OpenAI embedding model

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
    fields = [FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=2048), ]
    schema = CollectionSchema(fields, description="RAG text embeddings")
    if collection_name not in list_collections():
        Collection(name=collection_name, schema=schema)
    return Collection(collection_name)


def list_collections():
    return utility.list_collections()


def drop_collection(collection_name: str = COLLECTION_NAME):
    """
    Drop the Milvus collection if it exists.
    """
    from pymilvus import utility
    if collection_name in utility.list_collections():
        utility.drop_collection(collection_name)


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


def insert_embedding(embedding: list[float], text: str, collection_name: str = COLLECTION_NAME):
    """
    Insert a single embedding and its corresponding text into the collection.
    This function is optimized for single item insertion.
    """
    if collection_name not in list_collections():
        create_collection(collection_name)
    col = Collection(collection_name)

    # Validate input
    if not isinstance(embedding, list):
        raise ValueError("embedding must be a list of floats")
    if not isinstance(text, str):
        raise ValueError("text must be a string")

    # Debug information
    print(f"Inserting single embedding, length: {len(embedding)}")

    # Insert using entity format (most reliable for Milvus)
    try:
        entity = [{"embedding": embedding, "text": text}]
        col.insert(entity)

        # Build index if needed and load collection
        build_index(collection_name)
        load_collection(collection_name)
        return True
    except Exception as e:
        print(f"Error inserting embedding: {e}")
        raise


def insert_embeddings(embeddings: list[list[float]], texts: list[str],
                      collection_name: str = COLLECTION_NAME):
    """
    Insert multiple embeddings and their corresponding texts into the collection.
    This function is for batch insertion of multiple items.
    """
    if collection_name not in list_collections():
        create_collection(collection_name)
    col = Collection(collection_name)

    # Debug information
    print(f"Embeddings: {len(embeddings)}, Texts: {len(texts)}")
    if len(embeddings) > 0:
        print(f"Sample embedding[0]: {embeddings[0][:10]}...")

    # Validate input
    if not isinstance(embeddings, list):
        raise ValueError("embeddings must be a list of list of floats")
    if not isinstance(texts, list):
        raise ValueError("texts must be a list of strings")
    if len(embeddings) != len(texts):
        raise ValueError("embeddings and texts must have the same length")

    # Validate each embedding and text
    for i, (emb, txt) in enumerate(zip(embeddings, texts)):
        if not isinstance(emb, list):
            raise ValueError(f"embedding at index {i} must be a list of floats")
        if not isinstance(txt, str):
            raise ValueError(f"text at index {i} must be a string")

    # Insert the data using row-based format (most reliable for Milvus)
    try:
        # Create entities as a list of dictionaries (row-based format)
        entities = [{"embedding": emb, "text": txt} for emb, txt in zip(embeddings, texts)]

        # Insert data
        col.insert(entities)

        # Build index if needed and load collection
        build_index(collection_name)
        load_collection(collection_name)
        return True
    except Exception as e:
        print(f"Error inserting embeddings: {e}")
        raise


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
                     collection_name: str = COLLECTION_NAME):
    # Ensure collection exists
    if collection_name not in list_collections():
        create_collection(collection_name)
        # If collection is empty, return empty results
        return []

    # Build index if needed
    build_index(collection_name)

    # Load collection into memory
    col = load_collection(collection_name)

    # Perform search
    try:
        results = col.search([embedding], "embedding",
            param={"metric_type": "L2", "params": {"nprobe": 10}}, limit=top_k,
            output_fields=["text"], )
        return results
    except Exception as e:
        print(f"Search error: {e}")
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
    # Ensure collection exists
    if collection_name not in list_collections():
        create_collection(collection_name)
        # If collection is empty, return empty results
        return []
    
    # Load collection into memory
    col = load_collection(collection_name)
    
    try:
        # Query all entries
        results = col.query(
            expr="id > 0",  # Query all entries
            output_fields=["id", "text"],
            limit=limit
        )
        return results
    except Exception as e:
        print(f"Error getting all entries: {e}")
        # Return empty results on error
        return []
