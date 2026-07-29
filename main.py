import os, time, shutil
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel
from kb import KnowledgeBase
from llm_client import GroqClient

load_dotenv()
app = FastAPI(title="AI Knowledge Base Assistant with PDF RAG")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SIMILARITY_THRESHOLD = float(os.environ.get("SIMILARITY_THRESHOLD", 0.2))
kb = KnowledgeBase(similarity_threshold=SIMILARITY_THRESHOLD)
_llm_client = None

def get_llm_client() -> GroqClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = GroqClient()
    return _llm_client

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    answer: str
    source: str
    matched_question: str | None = None
    response_time_ms: float

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "stats": kb.stats()})

@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest):
    start = time.perf_counter()
    question = payload.question.strip()
    if not question:
        return AskResponse(answer="Please enter a question.", source="cache", response_time_ms=0)

    # 1. Check Q&A Semantic Cache First
    hit = kb.search(question)
    if hit is not None:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return AskResponse(
            answer=hit["answer"],
            source="cache",
            matched_question=hit["matched_question"],
            response_time_ms=round(elapsed_ms, 2)
        )

    # 2. Search PDF Vector Chunks for Context (using max_distance=1.5)
    pdf_chunks = kb.retrieve_pdf_context(question, n_results=3, max_distance=1.5)
    context_str = "\n---\n".join(pdf_chunks) if pdf_chunks else None

    # 3. Query LLM with retrieved context (RAG)
    answer = get_llm_client().ask(question, context=context_str)

    # 4. Save result to Semantic Cache
    kb.add(question, answer)
    elapsed_ms = (time.perf_counter() - start) * 1000

    source_label = "groq_pdf_rag" if context_str else "groq"
    return AskResponse(answer=answer, source=source_label, response_time_ms=round(elapsed_ms, 2))

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Endpoint to upload a PDF document and index its text into ChromaDB."""
    if not file.filename.endswith(".pdf"):
        return {"error": "Only PDF files are supported."}

    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        chunks_indexed = kb.add_pdf(temp_path)
        return {
            "status": "success",
            "filename": file.filename,
            "chunks_indexed": chunks_indexed,
            "kb_stats": kb.stats()
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/kb")
def view_kb():
    """Inspect stored questions and PDF chunks in the Knowledge Base."""
    data = kb.collection.get()
    entries = []
    if data and data.get("documents"):
        for doc, meta in zip(data["documents"], data["metadatas"]):
            entries.append({
                "content": doc,
                "metadata": meta
            })
    return {"count": len(entries), "entries": entries}

@app.get("/stats")
def stats():
    return kb.stats()

@app.post("/reset")
def reset():
    kb.clear()
    return {"status": "cleared", **kb.stats()}