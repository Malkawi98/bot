from langchain_community.document_loaders import WebBaseLoader
from markitdown import MarkItDown
from .embedding import EmbeddingService
from .milvus_client import connect_to_milvus, create_collection, insert_embedding, search_embedding
from langchain.text_splitter import RecursiveCharacterTextSplitter



class RAGService:
    def __init__(self, enable_plugins: bool = False):
        self.md = MarkItDown(enable_plugins=enable_plugins)
        self.embedder = EmbeddingService()
        connect_to_milvus()
        create_collection()

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

    def add_text_to_milvus(self, text: str):
        splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
        chunks = splitter.split_text(text)
        for chunk in chunks:
            if len(chunk) > 2048:
                chunk = chunk[:2048]  # Truncate to fit Milvus VARCHAR limit
            embedding = [self.embedder.embed(chunk)]  # Ensure shape [1, D]
            insert_embedding(embedding, chunk)

    def search_similar(self, query: str, top_k: int = 5):
        embedding = [self.embedder.embed(query)]  # Ensure shape [1, D]
        results = search_embedding(embedding, top_k=top_k)
        return results
