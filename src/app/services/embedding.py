import os
import openai

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-ada-002"  # You can change this to your preferred OpenAI embedding model

# Use the new OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

class EmbeddingService:
    def __init__(self, model: str = EMBEDDING_MODEL):
        self.model = model

    def embed(self, text: str) -> list[float]:
        response = client.embeddings.create(
            input=text,
            model=self.model
        )
        return response.data[0].embedding 