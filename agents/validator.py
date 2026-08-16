"""
Validator Agent — Cross-checks extracted data against source material.
An independent AI agent that verifies the Extractor's work, assigns confidence
scores, and flags potential hallucinations or errors.
"""

import json
from typing import Any, Optional

from agents.base import BaseAgent
from tools.pdf_tools import ParsedDocument
from utils.cost_tracker import CostTracker


class ValidatorAgent(BaseAgent):
    """
    Responsible for verifying extracted data against the source document.
    
    Key capabilities:
    - Cross-references each extracted field against the original text
    - Assigns confidence scores (HIGH / MEDIUM / LOW)
    - Flags potential hallucinations
    - Suggests corrections
    - Produces a validation report
    """

    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        super().__init__(
            name="Validator Agent",
            role="Data validation and verification specialist. You cross-check extracted data "
                 "against source documents to catch errors, hallucinations, and misattributions. "
                 "You are skeptical by nature and require evidence for every claim.",
            cost_tracker=cost_tracker,
        )

    def validate(
        self,
        extractions: list[dict],
        parsed_doc: ParsedDocument,
    ) -> list[dict]:
        """
        Validate each extracted record against the source document.
        Returns a list of validation results, one per extraction.
        """
        if not extractions:
            return []

        self.send_message(
            receiver="Orchestrator",
            message_type="status",
            content=f"Starting validation of {len(extractions)} records",
        )

        # Process in batches to manage token usage
        batch_size = 5
        all_validations = []

        for i in range(0, len(extractions), batch_size):
            batch = extractions[i:i + batch_size]
            batch_results = self._validate_batch(batch, parsed_doc, start_index=i)
            all_validations.extend(batch_results)

        # Compute summary statistics
        high = sum(1 for v in all_validations if v.get("overall_confidence") == "HIGH")
        medium = sum(1 for v in all_validations if v.get("overall_confidence") == "MEDIUM")
        low = sum(1 for v in all_validations if v.get("overall_confidence") == "LOW")

        self.send_message(
            receiver="Orchestrator",
            message_type="response",
            content={
                "status": "success",
                "records_validated": len(all_validations),
                "high_confidence": high,
                "medium_confidence": medium,
                "low_confidence": low,
            },
        )

        return all_validations

    def _validate_batch(
        self,
        batch: list[dict],
        parsed_doc: ParsedDocument,
        start_index: int = 0,
    ) -> list[dict]:
        """Validate a batch of extractions against the source."""
        # Get relevant source text
        source_text = parsed_doc.to_markdown()
        if len(source_text) > 40000:
            source_text = source_text[:40000] + "\n\n[... truncated ...]"

        records_json = json.dumps(batch, indent=2, default=str)

        prompt = f"""You are validating data extracted from a research paper by another AI agent.
Your job is to cross-check each extracted record against the original source text.

For each record, verify:
1. Is each field value actually present in the source document?
2. Is the value accurately transcribed (correct numbers, spelling, etc.)?
3. Is the source_location citation correct?
4. Are there any values that seem fabricated or hallucinated?

EXTRACTED RECORDS (to validate):
{records_json}

ORIGINAL SOURCE DOCUMENT:
{source_text}

For each record, return a validation result with:
- "record_index": the index of the record (starting from {start_index})
- "overall_confidence": "HIGH" (all fields verified), "MEDIUM" (some fields uncertain), or "LOW" (major issues found)
- "field_validations": object mapping field names to {{"verified": true/false, "note": "explanation"}}
- "issues": array of specific problems found (empty if none)
- "corrections": array of suggested corrections (empty if none)

Return a JSON object: {{"validations": [...]}}"""

        result = self.call_llm_json(
            prompt=prompt,
            system_instruction=(
                "You are a meticulous data validator. Your job is to verify that extracted "
                "data matches the source document. Be thorough but fair — only flag issues "
                "where there is a genuine discrepancy. Check numbers carefully, verify "
                "proper nouns and technical terms, and confirm that cited source locations "
                "are reasonable. If you cannot find a value in the source text, mark it "
                "as unverified with LOW confidence."
            ),
            task_description="Cross-validation of extracted data",
            temperature=0.1,
        )

        return result.get("validations", [])
