from langchain_community.document_loaders import WebBaseLoader
from markitdown import MarkItDown
from .embedding import EmbeddingService
from .milvus_client import connect_to_milvus, create_collection, insert_embedding, search_embedding
from langchain.text_splitter import RecursiveCharacterTextSplitter
from .markdown_converter import MarkdownConverter
import os
import uuid



class RAGService:
    def __init__(self, enable_plugins: bool = False):
        self.md = MarkItDown(enable_plugins=enable_plugins)
        self.markdown_converter = MarkdownConverter(enable_plugins=enable_plugins)
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
        embeddings = []
        texts = []
        for chunk in chunks:
            if not chunk.strip():
                continue  # skip empty or whitespace-only chunks
            if len(chunk) > 2048:
                chunk = chunk[:2048]  # Truncate to fit Milvus VARCHAR limit
            embedding = self.embedder.embed(chunk)
            print(f"Chunk: {chunk[:30]}... | Embedding type: {type(embedding)}, len: {len(embedding)}")  # Debug
            if hasattr(embedding, 'shape'):
                print(f"Embedding shape: {embedding.shape}")
            embeddings.append(embedding)
            texts.append(chunk)
        
        print(f"Embeddings: {len(embeddings)}, Texts: {len(texts)}")  # Debug
        if len(embeddings) > 0:
            print(f"Sample embedding[0] first 10 elements: {embeddings[0][:10]}")
        
        # Use insert_embeddings for multiple chunks
        if len(embeddings) > 0:
            from .milvus_client import insert_embeddings
            insert_embeddings(embeddings, texts)
        else:
            print("No valid chunks to insert")

    def search_similar(self, query: str, top_k: int = 5):
        # Get a single embedding vector for the query
        embedding = self.embedder.embed(query)
        
        # Debug information
        print(f"Search query: '{query[:30]}...' | Embedding type: {type(embedding)}, len: {len(embedding)}")
        
        # Pass the single embedding vector directly to search_embedding
        # Now returns a simplified format: list of dicts with 'text' and 'score' keys
        search_results = search_embedding(embedding, top_k=top_k)
        
        # Extract just the text from the results
        extracted_texts = []
        
        try:
            if search_results and len(search_results) > 0:
                print(f"Found {len(search_results)} search results")
                
                # Each result is already a dict with 'text' and 'score'
                for result in search_results:
                    if isinstance(result, dict) and 'text' in result:
                        text = result['text']
                        score = result.get('score', 0.0)
                        print(f"Using text with score {score}: {text[:50]}...")
                        extracted_texts.append(text)
                    else:
                        print(f"Result doesn't have expected format: {result}")
                
                print(f"Extracted {len(extracted_texts)} text results")
            else:
                print("No search results found")
                
        except Exception as e:
            import traceback
            print(f"Error extracting text from search results: {e}")
            print(traceback.format_exc())
        
        return extracted_texts
        
    def add_to_vector_store(self, content: str, title: str = None, tags: list = None):
        """Add content to the vector store with optional title and tags"""
        if not title:
            title = f"Content-{uuid.uuid4().hex[:8]}"
            
        if not tags:
            tags = ["imported"]
            
        # Truncate title if needed
        if len(title) > 100:
            title = title[:97] + "..."
            
        print(f"Adding content to vector store: {title}")
        
        # Split content into chunks and add to vector store
        self.add_text_to_milvus(content)
        
        return {"success": True, "title": title}
        
    def process_file(self, file_path: str, filename: str = None):
        """Process any supported file and add its content to the vector store using MarkdownConverter"""
        try:
            # Get file extension for tagging
            file_ext = os.path.splitext(file_path)[1].lower().replace('.', '')
            
            # For binary files like PDF, use PyPDF2 to extract text
            if file_ext in ['pdf']:
                try:
                    from PyPDF2 import PdfReader
                    reader = PdfReader(file_path)
                    content = ""
                    for page in reader.pages:
                        content += page.extract_text() + "\n\n"
                except ImportError:
                    # Fallback to simple text extraction if PyPDF2 is not available
                    with open(file_path, 'rb') as f:
                        content = str(f.read())
            else:
                # For text files, read directly and use MarkdownConverter
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        file_content = f.read()
                    content = self.markdown_converter.to_text(file_content)
                except UnicodeDecodeError:
                    # If we can't decode as text, treat as binary
                    with open(file_path, 'rb') as f:
                        content = str(f.read())
            
            # Add to vector store
            title = filename or os.path.basename(file_path)
            print(f"Processing file: {title} with content length: {len(content)}")
            
            # Make sure we have some actual content
            if not content or len(content.strip()) < 10:
                return {"success": False, "error": "Could not extract meaningful content from file"}
                
            result = self.add_to_vector_store(content, title, tags=[file_ext, "uploaded-file"])
            
            # Clean up the temporary file
            os.unlink(file_path)
            
            return result
        except Exception as e:
            import traceback
            print(f"Error processing file: {str(e)}")
            print(traceback.format_exc())
            # Clean up on error
            if os.path.exists(file_path):
                os.unlink(file_path)
            raise e
