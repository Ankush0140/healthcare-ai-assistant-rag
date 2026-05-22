import json
import re
from typing import Dict, Any, Tuple
from app.config import settings
from app.rag import rag_pipeline
from app.llm import llm_client

class AgentRouter:
    def __init__(self):
        self.slots_data = self._load_json(settings.slots_config_path)
        self.intents = self._load_json(settings.intents_config_path).get("reservation", [])

    def _load_json(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading JSON config from {path}: {e}")
            return {}

    def detect_intent(self, question: str) -> str:
        """Simple keyword-based intent detection."""
        question_lower = question.lower()
        for keyword in self.intents:
            # Word boundary matching
            if re.search(rf"\b{keyword}\b", question_lower):
                return "reservation"
        return "rag_qa"

    def _extract_reservation_entities(self, question: str) -> Tuple[str, str]:
        """Mock entity extraction for department and day."""
        question_lower = question.lower()
        
        # Simple extraction logic for demo
        departments = self.slots_data.keys()
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        
        found_dept = None
        found_day = None
        
        for dept in departments:
            if dept in question_lower:
                found_dept = dept
                break
                
        for day in days:
            if day in question_lower:
                found_day = day
                break
                
        return found_dept, found_day

    def run_reservation_tool(self, question: str) -> Dict[str, Any]:
        """Execute the mock reservation tool logic."""
        dept, day = self._extract_reservation_entities(question)
        
        if not dept or not day:
            return {
                "answer": "To check availability, please specify both a department (e.g., cardiology, neurology) and a day of the week.",
                "intent": "reservation",
                "department": dept,
                "day": day,
                "available_slots": []
            }
            
        slots = self.slots_data.get(dept, {}).get(day, [])
        
        if not slots:
            return {
                "answer": f"I'm sorry, but there are no available slots for {dept.capitalize()} on {day.capitalize()}.",
                "intent": "reservation",
                "department": dept,
                "day": day,
                "available_slots": []
            }
            
        slots_str = ", ".join(slots)
        return {
            "answer": f"Available {dept} slots for {day.capitalize()}: {slots_str}. Would you like to proceed with booking one?",
            "intent": "reservation",
            "department": dept,
            "day": day,
            "available_slots": slots
        }

    async def aroute_and_execute(self, question: str) -> Dict[str, Any]:
        """Route the user query to the correct pipeline and execute."""
        intent = self.detect_intent(question)
        
        if intent == "reservation":
            return self.run_reservation_tool(question)
            
        # Fallback to RAG QA
        chunks = rag_pipeline.retrieve(question)
        answer, confidence = await llm_client.generate_answer(question, chunks)
        
        # Format sources
        sources = []
        for c in chunks:
            sources.append({
                "source": c["metadata"]["source"],
                "page": c["metadata"]["page"],
                "preview": c["text"][:100] + "..."
            })
            
        return {
            "answer": answer,
            "intent": "rag_qa",
            "confidence": confidence,
            "sources": sources
        }

agent_router = AgentRouter()
