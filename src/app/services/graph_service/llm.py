import os
from langchain_openai import ChatOpenAI
from app.core.config import settings

# Ensure OPENAI_API_KEY is set in your .env or environment
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Choose your model
llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=OPENAI_API_KEY)

# You might want a separate, cheaper/faster model for classification
classifier_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key=OPENAI_API_KEY)
