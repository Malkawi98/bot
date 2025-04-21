from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl, ValidationError
from typing import Optional
from app.services.rag import RAGService

router = APIRouter(tags=["rag"])
rag_service = RAGService()

class RAGRequest(BaseModel):
    url: Optional[HttpUrl] = None

@router.post("/rag/context")
async def rag_context(
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    if not url and not file:
        raise HTTPException(status_code=400, detail="Either a URL or a file must be provided.")

    if url:
        try:
            # Strictly validate the URL
            valid_url = HttpUrl.validate(url)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Invalid URL format.")
        try:
            text = rag_service.get_website_text(str(valid_url))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to load URL: {e}")
        return {"source": "url", "text": text}

    if file:
        # Accept only files that MarkItDown supports (e.g., .md, .markdown, .txt)
        if not file.filename.lower().endswith((".md", ".markdown", ".txt")):
            raise HTTPException(status_code=400, detail="Only markdown or text files are supported.")
        content = (await file.read()).decode("utf-8")
        text = rag_service.get_markdown_text(content)
        return {"source": "file", "text": text} 