import httpx
from typing import List, Dict, Any, Tuple
from app.config import settings

class LLMClient:
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.timeout = settings.llm_timeout
        self.temperature = settings.llm_temperature

    def _build_prompt(self, question: str, context_chunks: List[Dict[str, Any]]) -> str:
        """Construct a healthcare-safe prompt grounded in context."""
        context_text = "\n\n".join([f"[Source: {c['metadata']['source']}, Page {c['metadata']['page']}]\n{c['text']}" for c in context_chunks])
        
        prompt = f"""You are a professional, helpful healthcare AI assistant.
Your task is to answer the user's question based strictly on the provided document context.

RULES:
1. ONLY use information from the provided context. Do NOT guess or use outside knowledge.
2. If the context does not contain the answer, reply exactly with: "I could not find this information in the provided documents."
3. Never provide medical diagnoses or unsafe medical advice.
4. Keep your answer concise and professional.

CONTEXT:
{context_text}

QUESTION:
{question}

ANSWER:"""
        return prompt

    async def generate_answer(self, question: str, context_chunks: List[Dict[str, Any]]) -> Tuple[str, float]:
        """
        Generate an answer using Gemma via Ollama.
        Returns the answer and a confidence score based on similarity of retrieved chunks.
        """
        if not context_chunks:
            return "I could not find this information in the provided documents.", 0.0

        prompt = self._build_prompt(question, context_chunks)
        
        # Calculate mock confidence based on average similarity scores of retrieved chunks
        avg_similarity = sum(c.get('similarity', 0) for c in context_chunks) / len(context_chunks)
        # Scale to max 1.0 (assuming similarities hover around 0.3 to 1.0)
        confidence = round(min(1.0, avg_similarity), 2)
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                result = response.json()
                return result.get("response", "").strip(), confidence
        except httpx.TimeoutException:
            raise Exception("LLM connection timed out.")
        except httpx.RequestError as e:
            raise Exception(f"Failed to connect to LLM: {str(e)}")

llm_client = LLMClient()
