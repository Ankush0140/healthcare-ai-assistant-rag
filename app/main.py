import os
import logging
import uuid
import glob
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import httpx

from app.config import settings
from app.rag import rag_pipeline
from app.agent import agent_router

# ==========================================
# Logging Configuration
# ==========================================
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(settings.log_dir, 'app.log'))
    ]
)
logger = logging.getLogger("healthcare_ai")

# ==========================================
# Startup Event (Auto-Ingestion)
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Auto-ingest PDFs from the data folder on startup."""
    logger.info("Starting up: Checking for PDFs to auto-ingest in data folder...")
    pdf_files = glob.glob(os.path.join(settings.upload_dir, "*.pdf"))
    
    if not pdf_files:
        logger.info(f"No PDFs found in {settings.upload_dir}.")
    else:
        for pdf_path in pdf_files:
            filename = os.path.basename(pdf_path)
            logger.info(f"Auto-ingesting {filename}...")
            try:
                chunks = rag_pipeline.ingest_document(pdf_path, filename)
                logger.info(f"Success: {filename} ({chunks} chunks stored)")
            except Exception as e:
                logger.error(f"Failed to auto-ingest {filename}: {e}")
                
    yield
    logger.info("Shutting down...")

# ==========================================
# FastAPI Setup
# ==========================================
app = FastAPI(
    title="Healthcare AI Assistant",
    description="RAG-based AI assistant for healthcare documents with a reservation intent router.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for the frontend
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")

# ==========================================
# Models
# ==========================================
class AskRequest(BaseModel):
    question: str = Field(..., description="The user's question or command")

from typing import Optional

class AskResponse(BaseModel):
    intent: str
    answer: str
    confidence: float = 0.0
    sources: list = []
    department: Optional[str] = None
    day: Optional[str] = None
    available_slots: list = []

# ==========================================
# Endpoints
# ==========================================
@app.get("/health")
async def health_check():
    """Check health of the API and its dependencies (Ollama)."""
    ollama_status = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(settings.ollama_base_url)
            if resp.status_code == 200:
                 ollama_status = True
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
        
    return {
        "status": "healthy",
        "ollama_available": ollama_status,
        "chromadb_available": True # If app runs, chromadb (embedded) is up
    }

@app.get("/documents")
async def list_documents():
    """List all PDFs available in the backend data folder."""
    pdf_files = glob.glob(os.path.join(settings.upload_dir, "*.pdf"))
    documents = [os.path.basename(f) for f in pdf_files]
    return {"documents": documents}

@app.post("/ingest")
async def manual_ingest_trigger():
    """Manually trigger ingestion of PDFs in the data folder."""
    pdf_files = glob.glob(os.path.join(settings.upload_dir, "*.pdf"))
    results = []
    
    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        try:
            chunks = rag_pipeline.ingest_document(pdf_path, filename)
            results.append({"filename": filename, "chunks": chunks, "status": "success"})
        except Exception as e:
            results.append({"filename": filename, "error": str(e), "status": "failed"})
            
    return {"results": results}

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """Ask a question. Will be routed to RAG QA or Reservation Tool based on intent."""
    logger.info(f"Received question: {request.question}")
    
    try:
        result = await agent_router.aroute_and_execute(request.question)
        logger.info(f"Resolved with intent: {result.get('intent')}")
        return result
    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
