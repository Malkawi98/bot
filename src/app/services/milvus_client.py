from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
from pymilvus import utility
import os

from app.core.config import settings

MILVUS_HOST = "milvus"  # Docker service name from docker-compose
MILVUS_PORT = "19530"

COLLECTION_NAME = "rag_embeddings"
EMBEDDING_DIM = 384  # Adjust to your embedding model's output size


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
    ]
    schema = CollectionSchema(fields, description="RAG text embeddings")
    if collection_name not in list_collections():
        Collection(name=collection_name, schema=schema)
    return Collection(collection_name)


def list_collections():
    return utility.list_collections()


def insert_embedding(embedding: list[float], text: str, collection_name: str = COLLECTION_NAME):
    col = Collection(collection_name)
    # Ensure embedding is a list of floats and text is a string
    if not (isinstance(embedding, list) and all(isinstance(x, float) for x in embedding)):
        raise ValueError("embedding must be a list of floats")
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    # Insert as a single row using a list of dicts (row-based insert)
    col.insert([
        {"embedding": embedding, "text": text}
    ])

def search_embedding(embedding: list[float], top_k: int = 5, collection_name: str = COLLECTION_NAME):
    col = Collection(collection_name)
    results = col.search(
        [embedding],
        "embedding",
        param={"metric_type": "L2", "params": {"nprobe": 10}},
        limit=top_k,
        output_fields=["text"],
    )
    return results 