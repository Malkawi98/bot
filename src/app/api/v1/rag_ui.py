from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from app.services.rag import RAGService
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="src/app/templates")
router = APIRouter(tags=["rag-ui"])
rag_service = RAGService()

@router.get("/rag/ui", response_class=HTMLResponse)
async def rag_form(request: Request):
    return templates.TemplateResponse("rag_form.html", {"request": request, "result": None, "error": None, "search_results": None})

@router.post("/rag/ui", response_class=HTMLResponse)
async def rag_submit(
    request: Request,
    url: str = Form(""),
    file: UploadFile = File(None),
    search_query: str = Form("")
):
    result = None
    error = None
    search_results = None
    # If search_query is provided, perform a similarity search
    if search_query:
        try:
            search_results = rag_service.search_similar(search_query)
        except Exception as e:
            error = f"Search error: {e}"
    # Otherwise, process and store new text
    elif url:
        try:
            text = rag_service.get_website_text(url)
            rag_service.add_text_to_milvus(text)
            result = f"Text extracted and stored in Milvus.\nPreview:\n{text[:500]}{'...' if len(text) > 500 else ''}"
        except Exception as e:
            error = str(e)
    elif file:
        if not file.filename.lower().endswith((".md", ".markdown", ".txt")):
            error = "Only markdown or text files are supported."
        else:
            content = (await file.read()).decode("utf-8")
            text = rag_service.get_markdown_text(content)
            rag_service.add_text_to_milvus(text)
            result = f"Text extracted and stored in Milvus.\nPreview:\n{text[:500]}{'...' if len(text) > 500 else ''}"
    else:
        error = "Please provide a URL, upload a file, or enter a search query."
    return templates.TemplateResponse("rag_form.html", {"request": request, "result": result, "error": error, "search_results": search_results}) 