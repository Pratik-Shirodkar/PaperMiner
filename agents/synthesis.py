"""
Synthesis Agent — Compares extractions across multiple papers to
generate cross-paper comparison tables and synthesis summaries.
"""

import json
from typing import Optional

from agents.base import BaseAgent
from utils.cost_tracker import CostTracker


class SynthesisAgent(BaseAgent):
    """
    Compares and synthesizes extractions across multiple papers.

    Key capabilities:
    - Cross-paper comparison tables
    - Identify consensus and disagreements
    - Highlight best-performing methods across papers
    - Generate synthesis summaries
    """

    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        super().__init__(
            name="Synthesis Agent",
            role="Cross-paper synthesis specialist. You compare structured extractions "
                 "across multiple research papers to identify patterns, consensus, "
                 "disagreements, and best-performing methods.",
            cost_tracker=cost_tracker,
        )

    def synthesize(
        self,
        batch_results: list[dict],
        schema_name: str,
    ) -> dict:
        """
        Synthesize extractions across multiple papers.

        Args:
            batch_results: List of pipeline results (one per paper)
            schema_name: The schema used for extraction

        Returns:
            Synthesis report with comparisons and insights
        """
        self.send_message(
            receiver="Orchestrator",
            message_type="status",
            content=f"Synthesizing results from {len(batch_results)} papers...",
        )

        # Gather all extractions with source paper info
        all_records = []
        for result in batch_results:
            filename = result.get("filename", "unknown")
            for record in result.get("extractions", []):
                enriched = {**record, "_source_paper": filename}
                all_records.append(enriched)

        if not all_records:
            return {
                "status": "empty",
                "message": "No records to synthesize",
                "comparison_table": [],
                "synthesis_summary": "",
            }

        # Prepare data for LLM
        records_json = json.dumps(all_records[:50], indent=2, default=str)  # Cap at 50

        paper_list = [r.get("filename", "?") for r in batch_results]
        papers_str = "\n".join(f"  - {p}" for p in paper_list)

        prompt = f"""You are analyzing structured data extracted from {len(batch_results)} research papers.
Schema used: {schema_name}

Papers analyzed:
{papers_str}

ALL EXTRACTED RECORDS (across all papers):
{records_json}

Generate a comprehensive synthesis:

1. **Comparison Table**: Create a summary comparison of key metrics across papers
2. **Consensus**: What findings are consistent across papers?
3. **Disagreements**: Where do papers report conflicting results?
4. **Best Performers**: Which methods/models/drugs performed best overall?
5. **Gaps**: What data is missing from some papers but present in others?
6. **Key Takeaways**: 3-5 actionable insights from the cross-paper analysis

Return a JSON object:
{{
  "comparison_table": [
    {{"paper": "filename", "key_metric_1": "value", "key_metric_2": "value", ...}}
  ],
  "consensus": ["finding 1", "finding 2"],
  "disagreements": ["disagreement 1"],
  "best_performers": [{{"category": "...", "winner": "...", "value": "...", "paper": "..."}}],
  "gaps": ["gap 1"],
  "key_takeaways": ["takeaway 1", "takeaway 2", "takeaway 3"],
  "synthesis_narrative": "A 2-3 paragraph narrative summary of findings across all papers."
}}
"""

        try:
            result = self.call_llm_json(
                prompt=prompt,
                system_instruction=(
                    "You are an expert research synthesizer. Compare results across "
                    "multiple papers objectively. Use precise numbers from the data. "
                    "Clearly distinguish consensus from speculation. Identify methodological "
                    "differences that might explain conflicting results."
                ),
                task_description="Cross-paper synthesis",
                temperature=0.3,
            )

            self.send_message(
                receiver="Orchestrator",
                message_type="response",
                content={
                    "status": "success",
                    "papers_compared": len(batch_results),
                    "total_records": len(all_records),
                    "takeaways": len(result.get("key_takeaways", [])),
                },
            )

            result["status"] = "success"
            result["papers_analyzed"] = len(batch_results)
            result["total_records_compared"] = len(all_records)
            return result

        except Exception as e:
            self.send_message(
                receiver="Orchestrator",
                message_type="error",
                content=f"Synthesis failed: {str(e)}",
            )
            return {
                "status": "error",
                "error": str(e),
                "comparison_table": [],
                "synthesis_summary": "",
            }
