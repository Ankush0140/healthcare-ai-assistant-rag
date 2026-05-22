import fitz  # PyMuPDF
import chromadb
import uuid
import os
from typing import List, Dict, Any
from app.config import settings
from app.embeddings import embedder

class RAGPipeline:
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(path=settings.chroma_db_dir)
        self.collection = self.chroma_client.get_or_create_collection(name=settings.chroma_collection)

    def parse_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract text from PDF page by page."""
        doc = fitz.open(file_path)
        pages_data = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            if text.strip():
                pages_data.append({
                    "page_number": page_num + 1,
                    "text": text
                })
        return pages_data

    def chunk_text(self, text: str, page_number: int, source_file: str) -> List[Dict[str, Any]]:
        """Split text into overlapping chunks."""
        chunks = []
        chunk_size = settings.chunk_size
        overlap = settings.chunk_overlap
        
        start = 0
        chunk_idx = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            
            # Avoid extremely small tail chunks unless it's the only chunk
            if len(chunk_text) > 50 or start == 0:
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "source": source_file,
                        "page": page_number,
                        "chunk_index": chunk_idx
                    }
                })
                chunk_idx += 1
                
            start += (chunk_size - overlap)
            
        return chunks

    def ingest_document(self, file_path: str, filename: str) -> int:
        """Process a PDF and store its chunks in ChromaDB."""
        pages = self.parse_pdf(file_path)
        all_chunks = []
        
        for page in pages:
            chunks = self.chunk_text(page["text"], page["page_number"], filename)
            all_chunks.extend(chunks)
            
        if not all_chunks:
            return 0
            
        # Process in batches if there are many chunks
        texts = [chunk["text"] for chunk in all_chunks]
        metadatas = [chunk["metadata"] for chunk in all_chunks]
        ids = [str(uuid.uuid4()) for _ in all_chunks]
        
        # Generate embeddings
        embeddings = embedder.embed_texts(texts)
        
        # Store in ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts
        )
        
        return len(all_chunks)

    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        """Find the most relevant chunks for a question."""
        query_embedding = embedder.embed_text(query)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=settings.top_k
        )
        
        retrieved_chunks = []
        distances = results['distances'][0] if results['distances'] else []
        
        for i, doc in enumerate(results['documents'][0]):
            # ChromaDB uses cosine distance depending on config; smaller distance usually means more similar
            # If using default L2, distance represents L2. If using cosine, distance is 1-cosine_similarity.
            # Assuming default (L2 or cosine distance), we'll do a simple check.
            dist = distances[i]
            # Convert simple distance to a mock "similarity score" (1.0 = perfect match, 0.0 = terrible)
            # This logic depends greatly on ChromaDB's underlying distance function.
            # Using a simplified check: smaller distance = higher similarity.
            similarity = max(0.0, 1.0 - (dist / 2.0))
            
            if similarity >= settings.similarity_threshold:
                retrieved_chunks.append({
                    "text": doc,
                    "metadata": results['metadatas'][0][i],
                    "similarity": round(similarity, 3)
                })
                
        return retrieved_chunks

rag_pipeline = RAGPipeline()
