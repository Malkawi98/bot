from langchain_community.document_loaders import WebBaseLoader

from markitdown import MarkItDown



class RAGService:
    def __init__(self, enable_plugins: bool = False):
        self.md = MarkItDown(enable_plugins=enable_plugins)

    def get_website_text(self, url: str) -> str:
        """Fetch and extract main text content from a website using LangChain WebBaseLoader."""
        loader = WebBaseLoader(url)
        docs = loader.load()
        # Concatenate all document page contents
        text = "\n".join(doc.page_content for doc in docs)
        return text

    def get_markdown_text(self, markdown_text: str) -> str:
        """Convert markdown to plain text using markitdown."""
        result = self.md.convert(markdown_text)
        return result.text_content

    def retrieve_context(self, source: str, is_url: bool = True) -> str:
        """Generic method to retrieve context from a URL or markdown string."""
        if is_url:
            return self.get_website_text(source)
        else:
            return self.get_markdown_text(source)

