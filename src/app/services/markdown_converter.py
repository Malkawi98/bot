import os
import tempfile
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
        # The markitdown library is designed to work with files, not strings
        # So we need to save the text to a temporary file first
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.md', delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(markdown_text)
        
        try:
            # Now we can use the convert method with the file path
            result = self.md.convert(temp_file_path)
            return result.text_content
        except Exception as e:
            print(f"Error converting markdown: {e}")
            # Fallback to simple text extraction
            return markdown_text
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    print(f"Error deleting temporary file: {e}")
