import os

from dotenv import load_dotenv
from langchain_openai import OpenAI
from markitdown import MarkItDown

load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


class MarkdownConverter:
    def __init__(self, enable_plugins: bool = False):
        self.md = MarkItDown(enable_plugins=enable_plugins, llm_client=client, llm_model="gpt-4o")

    def to_text(self, markdown_text: str) -> str:
        """Convert markdown to plain text (strips formatting)."""
        result = self.md.convert(markdown_text)
        return result.text_content
