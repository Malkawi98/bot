from langchain_community.document_loaders import WebBaseLoader
from markitdown import MarkItDown
from .embedding import EmbeddingService
from .milvus_client import connect_to_milvus, create_collection, insert_embedding, search_embedding
from langchain.text_splitter import RecursiveCharacterTextSplitter
from .markdown_converter import MarkdownConverter
import os
import uuid
import langdetect
from typing import Optional, List, Dict, Any



class RAGService:
    def __init__(self, enable_plugins: bool = False):
        self.md = MarkItDown(enable_plugins=enable_plugins)
        self.markdown_converter = MarkdownConverter(enable_plugins=enable_plugins)
        self.embedder = EmbeddingService()
        self.supported_languages = ['en', 'ar']  # English and Arabic support
        connect_to_milvus()
        create_collection()

    def get_website_text(self, url: str) -> str:
        """Fetch and extract main text content from a website using LangChain WebBaseLoader."""
        loader = WebBaseLoader(url)
        docs = loader.load()
        # Concatenate all document page contents
        text = "\n".join(doc.page_content for doc in docs)
        
        # Detect language for logging
        try:
            lang = langdetect.detect(text)
            print(f"Detected language from URL content: {lang}")
        except:
            print("Could not detect language from URL content")
            
        return text

    def get_markdown_text(self, markdown_text: str) -> str:
        """Convert markdown to plain text using markitdown."""
        try:
            # Use convert_string instead of convert to handle text content directly
            result = self.md.convert_string(markdown_text)
            return result.text_content
        except Exception as e:
            print(f"Error converting markdown text: {e}")
            # If conversion fails, return the original text
            return markdown_text

    def retrieve_context(self, source: str, is_url: bool = True) -> str:
        """Generic method to retrieve context from a URL or markdown string."""
        if is_url:
            return self.get_website_text(source)
        else:
            return self.get_markdown_text(source)

    def add_text_to_milvus(self, text: str, language: Optional[str] = None):
        print(f"Adding text to Milvus, total length: {len(text)} characters")
        
        # Detect language if not provided
        if not language:
            try:
                language = langdetect.detect(text)
                # Map to our supported languages
                if language not in self.supported_languages:
                    # Default to English for non-supported languages
                    if language.startswith('ar'):
                        language = 'ar'
                    else:
                        language = 'en'
            except Exception as e:
                print(f"Language detection failed: {e}")
                language = 'en'  # Default to English if detection fails
        
        print(f"Processing text in language: {language}")
        
        # Use appropriate chunk sizes based on language
        # Arabic needs different chunking due to RTL and character complexity
        if language == 'ar':
            # Smaller chunks for Arabic
            splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=200)
        else:
            # Default chunking for other languages (including English)
            splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
        
        # Split the text into chunks
        chunks = splitter.split_text(text)
        print(f"Split text into {len(chunks)} chunks for language: {language}")
        
        embeddings = []
        texts = []
        languages = []
        
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue  # skip empty or whitespace-only chunks
                
            # Always truncate to ensure we're under the limit
            if len(chunk) > 2000:
                print(f"Chunk {i} exceeds 2000 chars ({len(chunk)}), truncating")
                chunk = chunk[:2000]  # Truncate to fit Milvus VARCHAR limit with some buffer
                
            # Double-check length to be absolutely sure
            if len(chunk) > 2048:
                print(f"Warning: Chunk {i} still exceeds 2048 chars ({len(chunk)}), truncating further")
                chunk = chunk[:2048]
                
            # Add language for each chunk
            languages.append(language)          
            # Generate embedding for this chunk
            try:
                embedding = self.embedder.embed(chunk)
                
                # Add to our lists
                embeddings.append(embedding)
                texts.append(chunk)
                
                # Add metadata including language
                chunk_metadata = {"language": language}
                metadata.append(chunk_metadata)
                
                if i < 2 or i == len(chunks) - 1:  # Log first two chunks and last chunk
                    print(f"Chunk {i}/{len(chunks)}: {len(chunk)} chars | Language: {language} | Preview: {chunk[:50]}...")
            except Exception as e:
                print(f"Error embedding chunk {i}: {e}")
        
        print(f"Generated {len(embeddings)} embeddings from {len(chunks)} chunks")
        
        # Use insert_embeddings for multiple chunks
        if len(embeddings) > 0:
            from .milvus_client import insert_embeddings_with_metadata
            insert_embeddings_with_metadata(embeddings, texts, metadata)
            print(f"Successfully inserted {len(embeddings)} chunks into vector store with language metadata")
            return len(embeddings)
        else:
            print("No valid chunks to insert")
            return 0

    def search_similar(self, query: str, top_k: int = 5, language: Optional[str] = None):
        """Search for similar text chunks to the query.
        
        Args:
            query: The query text to search for
            top_k: Number of results to return
            language: Optional language filter ('en' or 'ar')
        """
        # Detect query language if not specified
        if not language:
            try:
                language = self.embedder.detect_language(query)
            except:
                language = 'en'  # Default to English
        
        print(f"Search query in {language}: '{query[:30]}...'")
        
        # Get embedding for query
        query_embedding = self.embedder.embed(query)
        
        # Prepare language filter expression if language is specified
        filter_expr = None
        if language and language in self.supported_languages:
            filter_expr = f"language == '{language}'"
            print(f"Searching with language filter: {language}")
        
        # Search in Milvus with language filter
        from .milvus_client import search_embedding
        results = search_embedding(query_embedding, top_k=top_k, filter_expr=filter_expr)
        
        # If no results with language filter, try without filter
        if filter_expr and (not results or len(results) == 0):
            print(f"No results found for language '{language}', trying without language filter")
            results = search_embedding(query_embedding, top_k=top_k)
            
        return results
        
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
        
    def add_to_vector_store(self, content: str, title: str = None, tags: list = None, language: Optional[str] = None):
        """Add content to the vector store with optional title, tags, and language"""
        if not title:
            title = f"Content-{uuid.uuid4().hex[:8]}"
            
        if not tags:
            tags = ["imported"]
        
        # Detect language if not provided
        if not language:
            try:
                language = langdetect.detect(content)
            except:
                language = 'en'  # Default to English if detection fails
        
        # Add language to tags
        if language and language not in tags:
            tags.append(language)
            
        # Truncate title if needed
        if len(title) > 100:
            title = title[:97] + "..."
            
        print(f"Adding content to vector store: {title} (length: {len(content)} chars, language: {language})")
        
        # Check if content is too large and log a warning
        if len(content) > 100000:  # 100KB is quite large
            print(f"Warning: Very large content ({len(content)} chars) being added to vector store")
        
        # Split content into chunks and add to vector store with language metadata
        chunks_added = self.add_text_to_milvus(content, language=language)
        
        return {
            "success": True, 
            "title": title,
            "chunks_added": chunks_added,
            "content_length": len(content),
            "language": language
        }
        
    def process_file(self, file_path: str, filename: str = None):
        """Process any supported file and add its content to the vector store using MarkdownConverter"""
        try:
            # Get file extension for tagging
            file_ext = os.path.splitext(file_path)[1].lower().replace('.', '')
            title = filename or os.path.basename(file_path)
            
            print(f"Processing file: {title} with extension: {file_ext}")
            
            # For binary files like PDF, use PyPDF2 to extract text
            if file_ext in ['pdf']:
                try:
                    from PyPDF2 import PdfReader
                    reader = PdfReader(file_path)
                    content = ""
                    total_pages = len(reader.pages)
                    print(f"PDF has {total_pages} pages")
                    
                    for i, page in enumerate(reader.pages):
                        page_text = page.extract_text()
                        content += page_text + "\n\n"
                        if i < 2 or i == total_pages - 1:  # Log first two pages and last page
                            print(f"Extracted {len(page_text)} chars from page {i+1}/{total_pages}")
                except ImportError:
                    # Fallback to simple text extraction if PyPDF2 is not available
                    with open(file_path, 'rb') as f:
                        content = str(f.read())
                    print("Used fallback binary reading for PDF (PyPDF2 not available)")
            elif file_ext in ['docx', 'doc']:
                try:
                    # Try to use docx2txt if available
                    import docx2txt
                    content = docx2txt.process(file_path)
                    print(f"Extracted {len(content)} chars from Word document using docx2txt")
                except ImportError:
                    # Fallback to simple text extraction
                    with open(file_path, 'rb') as f:
                        content = str(f.read())
                    print("Used fallback binary reading for Word doc (docx2txt not available)")
            else:
                # For text files, read directly and use MarkdownConverter
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        file_content = f.read()
                    content = self.markdown_converter.to_text(file_content)
                    print(f"Extracted {len(content)} chars from text file")
                except UnicodeDecodeError:
                    # If we can't decode as text, treat as binary
                    with open(file_path, 'rb') as f:
                        content = str(f.read())
                    print("Used fallback binary reading due to UnicodeDecodeError")
            
            # Make sure we have some actual content
            if not content or len(content.strip()) < 10:
                print("Error: Could not extract meaningful content from file")
                return {"success": False, "error": "Could not extract meaningful content from file"}
            
            print(f"Adding file content to vector store: {len(content)} characters")
            
            # Add to vector store with chunking
            result = self.add_to_vector_store(content, title, tags=[file_ext, "uploaded-file"])
            
            # Clean up the temporary file
            try:
                os.unlink(file_path)
                print(f"Deleted temporary file: {file_path}")
            except Exception as e:
                print(f"Warning: Could not delete temporary file {file_path}: {e}")
            
            return result
        except Exception as e:
            import traceback
            print(f"Error processing file: {str(e)}")
            print(traceback.format_exc())
            # Clean up on error
            if os.path.exists(file_path):
                os.unlink(file_path)
            raise e
