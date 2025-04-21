from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from app.services.rag import RAGService
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="src/app/templates")
router = APIRouter(tags=["rag-ui"])
rag_service = RAGService()

@router.get("/rag/ui", response_class=HTMLResponse)
async def rag_form(request: Request):
    return templates.TemplateResponse("rag_form.html", {"request": request, "result": None, "error": None})

@router.post("/rag/ui", response_class=HTMLResponse)
async def rag_submit(
    request: Request,
    url: str = Form(""),
    file: UploadFile = File(None)
):
    result = None
    error = None
    if url:
        try:
            text = rag_service.get_website_text(url)
            result = text
        except Exception as e:
            error = str(e)
    elif file:
        if not file.filename.lower().endswith((".md", ".markdown", ".txt")):
            error = "Only markdown or text files are supported."
        else:
            content = (await file.read()).decode("utf-8")
            result = rag_service.get_markdown_text(content)
    else:
        error = "Please provide a URL or upload a file."
    return templates.TemplateResponse("rag_form.html", {"request": request, "result": result, "error": error}) 