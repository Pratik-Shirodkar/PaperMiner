"""
Hypothesis Generation and Research Gap Discovery Agent.
Analyzes structured extractions, contradictions, and ablation baselines to formulate
falsifiable scientific hypotheses, unexplored mechanisms, and experimental protocols.
"""

from typing import Any, Optional
from agents.base import BaseAgent
from schemas.base import ExtractionSchema


class HypothesisAgent(BaseAgent):
    """
    Autonomous Hypothesis Generator & Research Gap Engine.
    Examines extracted empirical findings to generate testable scientific hypotheses,
    quantify research blindspots, and design validation experiments.
    """

    def __init__(self, model_name: str = "gemini-flash-latest"):
        super().__init__(
            name="Hypothesis Generator",
            role="Autonomous Scientific Hypothesis & Research Gap Engine",
            model_name=model_name,
        )

    def generate_hypotheses(
        self,
        extractions: list[dict[str, Any]],
        schema: ExtractionSchema,
        document_context: str = "",
    ) -> dict[str, Any]:
        """
        Generate falsifiable hypotheses and detect research gaps from extracted findings.
        """
        self.send_message(
            receiver="Orchestrator",
            message_type="status",
            content=f"Synthesizing {len(extractions)} extracted data records to discover research gaps & hypotheses...",
        )

        prompt = f"""You are a Principal Scientific Investigator and Meta-Research Scientist.
Analyze the following extracted empirical data records from scientific literature:

EXTRACTION SCHEMA: {schema.name} - {schema.description}

EXTRACTED EMPIRICAL FINDINGS ({len(extractions)} records):
---
{extractions[:20]}
---

DOCUMENT CONTEXT / ABSTRACT SAMPLE:
---
{document_context[:3000]}
---

Based on these empirical findings, identify non-obvious patterns, parameter sensitivities, benchmark saturation points, or clinical contradictions to formulate 3 novel, falsifiable scientific hypotheses and identify 2 critical research gaps.

Return a JSON object with this exact structure:
{{
  "research_gaps": [
    {{
      "gap_title": "Concise title of the research blindspot or unexplored parameter space",
      "description": "Detailed explanation of what the current literature omits or leaves unanswered",
      "impact_potential": "High / Medium / Transformative",
      "suggested_investigation": "Specific experimental protocol or ablation needed to close this gap"
    }}
  ],
  "hypotheses": [
    {{
      "hypothesis_id": "H1",
      "title": "Concise Scientific Hypothesis Title",
      "formal_statement": "If [condition / architecture / intervention], then [falsifiable outcome / effect size], because [mechanistic rationale].",
      "rationale_from_evidence": "Specific empirical basis derived directly from the extracted records",
      "proposed_experiment": "Step-by-step experimental design, dataset, and metric to prove or refute this hypothesis",
      "falsification_criteria": "The exact threshold or condition under which this hypothesis is conclusively refuted",
      "novelty_score": 8.5,
      "feasibility_score": 9.0
    }}
  ],
  "meta_synthesis_summary": "2-3 sentences synthesizing the scientific frontier based on these extractions."
}}
"""

        result = self.call_llm_json(
            prompt=prompt,
            system_instruction=(
                "You are an elite research scientist. You generate rigorous, mathematically sound, "
                "or clinically actionable hypotheses grounded in empirical evidence. Avoid trivial or generic statements."
            ),
            task_description="Autonomous hypothesis and research gap generation",
        )

        self.send_message(
            receiver="Orchestrator",
            message_type="response",
            content={
                "status": "success",
                "hypothesis_count": len(result.get("hypotheses", [])),
                "gap_count": len(result.get("research_gaps", [])),
            },
        )

        return result
