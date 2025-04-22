from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
from pymilvus import utility

from app.core.config import settings

MILVUS_HOST = "milvus"  # Docker service name from docker-compose
MILVUS_PORT = "19530"

COLLECTION_NAME = "rag_embeddings"
EMBEDDING_DIM = 384  # Adjust to your embedding model's output size


def connect_to_milvus(alias: str = "default"):
    """
    Connect to Milvus with consistent connection settings.

    Args:
        alias: Connection alias name (default: "default")

    Returns:
        None
    """
    from pymilvus import connections

    # Determine whether to use secure connection based on URI
    secure = False if settings.MILVUS_URI.startswith("http://") else True

    # Set up connection parameters
    connection_args = {
        "uri": settings.MILVUS_URI,
        "token": settings.MILVUS_API_KEY,
        "secure": secure,
    }
    # Connect to Milvus
    try:
        connections.connect(alias=alias, **connection_args)
    except Exception as e:
        raise



# def connect_to_milvus():
#     connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)


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
    # For batch insert in the future:
    # col.insert([
    #     {"embedding": embedding1, "text": text1},
    #     {"embedding": embedding2, "text": text2},
    #     ...
    # ])


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