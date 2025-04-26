from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl, ValidationError
from typing import Optional, List, Dict, Any
from fastapi import status
from app.services.milvus_client import get_all_entries, reset_collection
from app.services.rag import RAGService
import os
import tempfile
import shutil

router = APIRouter(tags=["rag"])
rag_service = RAGService()

class RAGRequest(BaseModel):
    url: Optional[HttpUrl] = None

@router.post("/rag/context")
async def rag_context(
    background_tasks: BackgroundTasks,
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None)
):
    if not url and not file and not text:
        raise HTTPException(status_code=400, detail="Either a URL, file, or direct text must be provided.")

    if url:
        try:
            # Normalize the URL - make sure it has a scheme
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'https://' + url
                
            # Strictly validate the URL using Pydantic
            # HttpUrl doesn't have a validate method, so we create a temporary model
            class UrlModel(BaseModel):
                url: HttpUrl
            
            # Validate URL
            valid_url = UrlModel(url=url).url
            
            # Get the text content from the URL
            try:
                text = rag_service.retrieve_context(str(valid_url), is_url=True)
                
                if not text or len(text.strip()) < 10:
                    raise HTTPException(status_code=400, detail="Could not extract meaningful content from the URL.")
                
                # Add the content to the vector store in the background
                background_tasks.add_task(
                    rag_service.add_to_vector_store,
                    content=text,
                    title=f"URL: {url}",
                    tags=["url", "imported"]
                )
                
                return {"source": "url", "text": text[:1000] + "..." if len(text) > 1000 else text, "added_to_vector_store": True}
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to process URL content: {str(e)}")
        except ValidationError:
            raise HTTPException(status_code=400, detail="Invalid URL format. Please enter a valid URL.")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to process URL: {str(e)}")

    if text:
        try:
            # Process the text directly without creating a file
            # Add the content to the vector store in the background
            background_tasks.add_task(
                rag_service.add_to_vector_store,
                content=text,
                title="Direct Text Input",
                tags=["text", "imported"]
            )
            return {"source": "text", "text": text[:1000] + "..." if len(text) > 1000 else text, "added_to_vector_store": True}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to process text: {str(e)}")
            
    if file:
        try:
            # Accept any file type that our processor can handle
            content = await file.read()
            
            # Create a temporary file with a UUID as the filename to avoid any length issues
            import uuid
            file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else '.txt'
            temp_filename = f"{uuid.uuid4().hex}{file_ext}"
            temp_file_path = os.path.join(tempfile.gettempdir(), temp_filename)
            
            # Write content to the temporary file
            with open(temp_file_path, 'wb') as temp_file:
                temp_file.write(content)
                
            print(f"Created temporary file: {temp_file_path}")
            
            # For text files, try to decode and get text content for immediate display
            text = ""
            if file_ext in [".md", ".markdown", ".txt"]:
                try:
                    # Decode the content as text
                    text_content = content.decode("utf-8")
                    # Use the get_markdown_text method to convert to plain text
                    # This now uses convert_string instead of convert
                    text = text_content[:1000] + "..." if len(text_content) > 1000 else text_content
                except UnicodeDecodeError:
                    text = "Binary file content cannot be displayed directly."
            else:
                text = "File content will be processed and added to the knowledge base."
                
            # Process the file in the background
            background_tasks.add_task(
                rag_service.process_file,
                file_path=temp_file_path,
                filename=file.filename
            )
            
            return {"source": "file", "text": text, "added_to_vector_store": True}
        except Exception as e:
            # Clean up on error
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            import traceback
            print(f"Error processing file: {str(e)}\n{traceback.format_exc()}")
            raise HTTPException(status_code=400, detail=f"Failed to process file: {str(e)}") 

@router.post("/vector-store/upload")
async def upload_to_vector_store(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Upload a file to the vector store"""
    # Check file extension
    allowed_extensions = [".pdf", ".docx", ".txt", ".md", ".csv"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format. Allowed formats: {', '.join(allowed_extensions)}"
        )
    
    # Create a temporary file to store the uploaded content
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            # Write the uploaded file content to the temporary file
            shutil.copyfileobj(file.file, temp_file)
            temp_file_path = temp_file.name
        
        # Process the file using the unified process_file method
        background_tasks.add_task(
            rag_service.process_file,
            file_path=temp_file_path,
            filename=file.filename
        )
        
        return {"success": True, "message": f"File '{file.filename}' is being processed and added to the vector store."}
    
    except Exception as e:
        # Clean up the temporary file in case of an error
        if 'temp_file_path' in locals():
            os.unlink(temp_file_path)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        # Close the file object
        file.file.close()