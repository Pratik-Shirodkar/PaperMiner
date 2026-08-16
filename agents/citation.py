"""
Citation Agent — Spot-checks extracted claims by verifying that
cited references actually exist and match the claimed content.
Adds a citation verification layer to the extraction pipeline.
"""

import json
from typing import Optional

from agents.base import BaseAgent
from tools.pdf_tools import ParsedDocument
from utils.cost_tracker import CostTracker


class CitationAgent(BaseAgent):
    """
    Verifies citations referenced in extracted data.

    Key capabilities:
    - Checks if cited references exist in the paper's bibliography
    - Verifies that claims match the cited source context
    - Flags potentially fabricated or misattributed citations
    - Cross-references citation numbers with the reference list
    """

    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        super().__init__(
            name="Citation Agent",
            role="Citation verification specialist. You cross-check cited references "
                 "against the paper's bibliography and verify claim-source alignment.",
            cost_tracker=cost_tracker,
        )

    def verify_citations(
        self,
        extractions: list[dict],
        parsed_doc: ParsedDocument,
    ) -> list[dict]:
        """
        Verify citations in extracted records.

        For each extraction that references other papers (e.g., "method from [23]"),
        checks:
        1. Does reference [23] exist in the bibliography?
        2. Does the referenced paper plausibly support the claim?

        Returns a list of citation verification results.
        """
        self.send_message(
            receiver="Orchestrator",
            message_type="status",
            content=f"Verifying citations in {len(extractions)} records...",
        )

        # Extract the references section
        references_text = self._extract_references(parsed_doc)
        if not references_text:
            self.send_message(
                receiver="Orchestrator",
                message_type="response",
                content={"status": "skipped", "reason": "No references section found"},
            )
            return []

        # Build the verification prompt
        extractions_json = json.dumps(extractions[:15], indent=2, default=str)  # Cap at 15

        prompt = f"""You are verifying citations in data extracted from a research paper.

EXTRACTED RECORDS:
{extractions_json}

PAPER'S REFERENCES / BIBLIOGRAPHY:
{references_text[:8000]}

For each extracted record that mentions or cites another work (via [number], author names, or paper titles):
1. Check if the cited reference exists in the bibliography above
2. Assess whether the reference plausibly supports the claim being made
3. Flag any citation numbers that don't match the bibliography

Return a JSON object:
{{
  "citation_checks": [
    {{
      "record_index": 0,
      "cited_reference": "[23] or author name",
      "reference_found": true/false,
      "reference_title": "Title from bibliography if found",
      "claim_alignment": "STRONG" / "PLAUSIBLE" / "WEAK" / "UNVERIFIABLE",
      "notes": "explanation"
    }}
  ],
  "summary": {{
    "total_citations_checked": 5,
    "references_found": 4,
    "references_missing": 1,
    "potentially_fabricated": 0
  }}
}}
"""

        try:
            result = self.call_llm_json(
                prompt=prompt,
                system_instruction=(
                    "You are a meticulous citation checker. Verify that citation numbers "
                    "match entries in the bibliography. Be precise about reference numbers. "
                    "Only flag a citation as 'potentially fabricated' if the number clearly "
                    "doesn't exist in the reference list."
                ),
                task_description="Citation verification",
            )

            checks = result.get("citation_checks", [])
            summary = result.get("summary", {})

            self.send_message(
                receiver="Orchestrator",
                message_type="response",
                content={
                    "status": "success",
                    "citations_checked": summary.get("total_citations_checked", len(checks)),
                    "references_found": summary.get("references_found", 0),
                    "references_missing": summary.get("references_missing", 0),
                },
            )

            return result

        except Exception as e:
            self.send_message(
                receiver="Orchestrator",
                message_type="error",
                content=f"Citation verification failed: {str(e)}",
            )
            return {"citation_checks": [], "summary": {}}

    def _extract_references(self, parsed_doc: ParsedDocument) -> str:
        """Extract the references/bibliography section from the parsed document."""
        # Look for references section
        for section in parsed_doc.sections:
            title_lower = section.title.lower()
            if title_lower in ("references", "bibliography", "works cited", "literature"):
                return section.content

        # Fallback: search the full text for a references block
        text = parsed_doc.full_text
        markers = ["references\n", "bibliography\n", "REFERENCES\n"]
        for marker in markers:
            idx = text.lower().rfind(marker.lower())
            if idx != -1:
                return text[idx:idx + 10000]

        return ""
