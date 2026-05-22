# Healthcare AI Assistant using RAG and LLMs

This is a hackathon-style project for a Healthcare AI Assistant. It uses a Retrieval-Augmented Generation (RAG) pipeline to answer questions based on healthcare documents. It also implements a simple agentic intent router to handle mock appointment reservations.

## Project Architecture

- **Backend Framework**: FastAPI
- **LLM Engine**: Ollama running locally (Model: `gemma:2b`)
- **Embeddings Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Vector Database**: ChromaDB (Persistent)
- **Document Parsing**: PyMuPDF (`fitz`) for PDF text extraction.
- **Agent/Tool Workflow**: A keyword-based intent router that routes questions either to a RAG-based QA pipeline or a mock Reservation scheduling tool.

---

## Setup and Run Instructions

### Prerequisites
- Docker and Docker Compose installed
- Port `8000` available for the FastAPI application
- Port `11434` available for the Ollama service

### Running with Docker Compose (Recommended)

1. **Start the containers**
   ```bash
   docker-compose up -d --build
   ```

2. **Pull the LLM Model in Ollama**
   Since the Ollama image does not come with models pre-downloaded, you must pull the `gemma:2b` model manually inside the container:
   ```bash
   docker exec -it <project-folder-name>-ollama-1 ollama pull gemma:2b
   ```
   *(Note: Replace `<project-folder-name>` with your actual directory name, typically `healthcare-ai-assistant-ollama-1`)*

3. **Verify the Services**
   - The API should be accessible at `http://localhost:8000/docs` (Swagger UI)
   - You can check the health endpoint: `curl http://localhost:8000/health`

### Local Setup (Without Docker)
1. Install Python 3.11+.
2. Install dependencies: `pip install -r requirements.txt`
3. Install and run [Ollama](https://ollama.com/) locally.
4. Pull the model: `ollama pull gemma:2b`
5. Run the FastAPI server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

---

## Technical Details

### 1. LLM Used
The application uses **Gemma 2B (`gemma:2b`)** via Ollama. It was chosen because it is lightweight, runs well on local hardware, and provides strong zero-shot reasoning capabilities suitable for document-grounded question answering without requiring a cloud API.

### 2. Embedding Model
**`sentence-transformers/all-MiniLM-L6-v2`** is used for converting text chunks into dense vector embeddings. It's an efficient, fast, and highly capable model for semantic search tasks.

### 3. Vector Database
**ChromaDB** is used in persistent mode. It stores the document embeddings and metadata locally in the `./vector_store` directory, allowing for efficient similarity search without requiring an external database server.

### 4. Prompting Strategy
The prompt is designed to ensure safety and prevent hallucination. It explicitly rules out guessing and forces the LLM to only answer based on the retrieved context. It also includes a strict rule to prevent providing direct medical diagnosis or unsafe medical advice.
```text
You are a professional, helpful healthcare AI assistant.
Your task is to answer the user's question based strictly on the provided document context.

RULES:
1. ONLY use information from the provided context. Do NOT guess or use outside knowledge.
2. If the context does not contain the answer, reply exactly with: "I could not find this information in the provided documents."
3. Never provide medical diagnoses or unsafe medical advice.
4. Keep your answer concise and professional.
...
```

### 5. Agent/Tool Workflow
The application implements a basic intent router in `app/agent.py`. It checks incoming questions for reservation-specific keywords.
- **Intent: Reservation**: If the user asks about booking or slots, the request is routed to a mock tool `run_reservation_tool()`, which extracts the department and day, and returns available slots from a predefined JSON config.
- **Intent: RAG QA**: If it's a general question, it routes to the RAG pipeline, retrieves context from ChromaDB, and generates an answer using the LLM.

### 6. Dataset / Sources
Documents should be placed in the `/data` folder in PDF format. The application will auto-ingest any PDFs found in this folder upon startup.
Suggested datasets: Synthetic policies, MedlinePlus topics, WHO fact sheets. *(No real PHI is used in this project)*.

---

## API Examples

### 1. Health Check
```bash
curl -X GET http://localhost:8000/health
```

### 2. Manual Ingestion Trigger
Ingests all PDFs inside the `/data` folder:
```bash
curl -X POST http://localhost:8000/ingest
```

### 3. Ask a Question (RAG Pipeline)
```bash
curl -X POST http://localhost:8000/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "What is the policy for telehealth consultations?"}'
```

### 4. Ask a Question (Reservation Tool)
```bash
curl -X POST http://localhost:8000/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "Can I book a cardiology appointment for Monday?"}'
```

---

## Sample Questions and Responses

**Q: Can I book a cardiology appointment for Monday?**
- **Response**: "Available cardiology slots for Monday: 10:00 AM, 02:00 PM. Would you like to proceed with booking one?"
- **Intent**: `reservation`

**Q: What should I do if I experience side effects from the medication?** *(Assuming context exists in uploaded PDF)*
- **Response**: "Based on the discharge instructions, if you experience severe side effects, you should immediately contact your primary care physician or visit the emergency room."
- **Intent**: `rag_qa`

**Q: How do I treat a broken leg?** *(No context in document)*
- **Response**: "I could not find this information in the provided documents."
- **Intent**: `rag_qa`

---

## Limitations and Future Improvements

### Limitations
- **Basic Intent Router**: The router uses simple keyword matching which can fail on complex phrasings.
- **Static Chunking**: Text chunking is purely character-based and might break sentences mid-way, potentially losing semantic meaning.
- **Mock Entities**: Entity extraction for the reservation tool is naive and assumes exact matches for departments and days.

### Future Improvements
- Implement semantic routing using the LLM or a classification model instead of keyword matching.
- Add advanced chunking strategies (e.g., semantic chunking or recursive character splitting).
- Improve the agent workflow with tools like LangChain or CrewAI for multi-step reasoning.
- Implement conversational memory to support follow-up questions.
