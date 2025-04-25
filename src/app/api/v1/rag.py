from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl, ValidationError
from typing import Optional, List
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
    file: Optional[UploadFile] = File(None)
):
    if not url and not file:
        raise HTTPException(status_code=400, detail="Either a URL or a file must be provided.")

    if url:
        try:
            # Strictly validate the URL using Pydantic
            # HttpUrl doesn't have a validate method, so we create a temporary model
            class UrlModel(BaseModel):
                url: HttpUrl
            
            # Validate URL
            valid_url = UrlModel(url=url).url
        except ValidationError:
            raise HTTPException(status_code=400, detail="Invalid URL format.")
        try:
            # Get the text content from the URL
            text = rag_service.get_website_text(str(valid_url))
            
            # Add the content to the vector store in the background
            background_tasks.add_task(
                rag_service.add_to_vector_store,
                content=text,
                title=f"URL: {url}",
                tags=["url", "imported"]
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to load URL: {e}")
        return {"source": "url", "text": text, "added_to_vector_store": True}

    if file:
        # Accept any file type that our processor can handle
        content = await file.read()
        
        # Create a temporary file to store the uploaded content
        file_ext = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
            
        try:
            # For text files, try to decode and get text content for immediate display
            if file_ext in [".md", ".markdown", ".txt"]:
                try:
                    text_content = content.decode("utf-8")
                    text = rag_service.get_markdown_text(text_content)
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