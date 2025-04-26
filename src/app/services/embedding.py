import os
import openai
import langdetect

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# Use a model that has strong multilingual capabilities
EMBEDDING_MODEL = "text-embedding-3-large"  # Better multilingual support than ada-002

# Use the new OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

class EmbeddingService:
    def __init__(self, model: str = EMBEDDING_MODEL):
        self.model = model
    
    def detect_language(self, text: str) -> str:
        """Detect the language of the input text.
        
        Returns:
            str: Language code ('en' for English, 'ar' for Arabic, etc.)
        """
        try:
            return langdetect.detect(text)
        except:
            # Default to English if detection fails
            return "en"
    
    def embed(self, text: str) -> list[float]:
        """Generate embeddings for text in any language.
        
        The text-embedding-3-large model supports multiple languages including Arabic.
        """
        if not text or len(text.strip()) == 0:
            raise ValueError("Cannot embed empty text")
            
        # Detect language for logging/debugging
        lang = self.detect_language(text)
        print(f"Embedding text in detected language: {lang}")
        
        # Generate embeddings (same process for all languages with multilingual model)
        response = client.embeddings.create(
            input=text,
            model=self.model
        )
        return response.data[0].embedding