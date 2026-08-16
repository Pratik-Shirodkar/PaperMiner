"""
Conversational Research Co-Pilot Agent.
Answers research inquiries grounded strictly in extracted structured records
and PDF context with exact citations, confidence traces, and data synthesis.
"""

from typing import Any, Optional
from agents.base import BaseAgent
from utils.cost_tracker import CostTracker


class ResearchCopilotAgent(BaseAgent):
    """
    Evidence-grounded conversational co-pilot for querying extracted datasets.
    """

    def __init__(
        self,
        cost_tracker: Optional[CostTracker] = None,
        model_name: str = "gemini-flash-latest",
    ):
        super().__init__(
            name="Research Co-Pilot",
            role="Evidence-Grounded Scientific Q&A Engine",
            cost_tracker=cost_tracker,
            model_name=model_name,
        )

    def answer_query(
        self,
        query: str,
        extractions: list[dict[str, Any]],
        document_text: str = "",
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        """
        Answer a user research query grounded in the structured extractions and document text.
        """
        self.send_message(
            receiver="Orchestrator",
            message_type="status",
            content=f"Analyzing research query: '{query[:50]}...'",
        )

        history_context = ""
        if conversation_history:
            history_context = "\n".join([
                f"{msg.get('role', 'user').upper()}: {msg.get('content', '')}"
                for msg in conversation_history[-4:]
            ])

        prompt = f"""You are an expert Research Co-Pilot and Scientific Peer Reviewer.
Answer the following user question grounded strictly in the provided verified data records and document text.

USER QUERY:
{query}

PREVIOUS CONVERSATION CONTEXT:
{history_context or "None"}

EXTRACTED STRUCTURED DATABASE ({len(extractions)} verified records):
---
{extractions}
---

DOCUMENT CONTEXT SAMPLE:
---
{document_text[:4000]}
---

Instructions:
1. Provide a direct, authoritative, scientifically rigorous answer.
2. Explicitly cite the specific data rows, model names, metric values, or section locations.
3. If the user asks for comparisons, calculate differences, percentages, or speedups explicitly.
4. List the key supporting data records used to formulate this answer.

Return a JSON object:
{{
  "answer_markdown": "Rich markdown response answering the query with bolded metrics and structured bullet points",
  "supporting_records": ["Record 1 identifier / metric cited", "Record 2 identifier / metric cited"],
  "confidence_score": 0.98,
  "suggested_followups": [
    "Suggested insightful followup question 1",
    "Suggested insightful followup question 2"
  ]
}}
"""

        result = self.call_llm_json(
            prompt=prompt,
            system_instruction=(
                "You are an evidence-grounded research assistant. Ground every claim directly in the extracted numbers. "
                "Never hallucinate numbers that do not exist in the extracted database or document context."
            ),
            task_description="Grounded scientific query answering",
        )

        return result
