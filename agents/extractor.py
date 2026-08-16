"""
Extractor Agent — Schema-guided structured data extraction using Gemini.
This is the core AI agent: it reads parsed document content and fills
structured schemas with extracted values, citing source locations.
"""

import json
from typing import Any, Optional

from agents.base import BaseAgent
from schemas.base import ExtractionSchema
from tools.pdf_tools import ParsedDocument
from utils.cost_tracker import CostTracker


class ExtractorAgent(BaseAgent):
    """
    Responsible for extracting structured data from parsed documents.
    
    Key capabilities:
    - Schema-guided extraction using Gemini's structured output
    - Source citation for every extracted value
    - Multi-pass extraction for complex documents
    - Handles both tabular and prose-embedded data
    """

    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        super().__init__(
            name="Extractor Agent",
            role="Schema-guided data extractor. You read parsed research paper content and "
                 "extract structured data according to a defined schema, always citing where "
                 "in the document each value was found.",
            cost_tracker=cost_tracker,
        )

    def extract(
        self,
        parsed_doc: ParsedDocument,
        schema: ExtractionSchema,
    ) -> list[dict]:
        """
        Extract structured data from a parsed document using the given schema.
        
        Uses a multi-pass approach:
        1. First pass: Extract from tables (highest confidence source)
        2. Second pass: Extract from text sections
        3. Merge and deduplicate
        """
        self.send_message(
            receiver="Orchestrator",
            message_type="status",
            content=f"Starting extraction with schema: {schema.name}",
        )

        all_records: list[dict] = []

        # Pass 1: Extract from tables
        if parsed_doc.tables:
            table_records = self._extract_from_tables(parsed_doc, schema)
            all_records.extend(table_records)
            self.send_message(
                receiver="Orchestrator",
                message_type="status",
                content=f"Table extraction: found {len(table_records)} records",
            )

        # Pass 2: Extract from text content
        text_records = self._extract_from_text(parsed_doc, schema)
        
        # Merge, preferring table-sourced data but adding text-only findings
        merged = self._merge_records(all_records, text_records, schema)
        
        self.send_message(
            receiver="Orchestrator",
            message_type="response",
            content={
                "status": "success",
                "records_extracted": len(merged),
                "from_tables": len(all_records),
                "from_text": len(text_records),
            },
        )

        return merged

    def _extract_from_tables(
        self,
        parsed_doc: ParsedDocument,
        schema: ExtractionSchema,
    ) -> list[dict]:
        """Extract data from detected tables using Gemini."""
        if not parsed_doc.tables:
            return []

        tables_md = "\n\n".join(
            f"### Table from page {t.page_number}\n{t.to_markdown()}"
            for t in parsed_doc.tables
        )

        prompt = f"""{schema.to_prompt_description()}

Below are tables extracted from the research paper "{parsed_doc.filename}".
Extract all records that match the schema from these tables.

For the "source_location" field, specify which table and page the data came from.
If a field value is not found in the tables, use null.
Only extract data that is explicitly present — do NOT infer or hallucinate values.

TABLES:
{tables_md}

Return a JSON object with a "records" key containing an array of extracted records.
Each record should have the schema fields as keys.
If no matching data is found, return {{"records": []}}.
"""

        result = self.call_llm_json(
            prompt=prompt,
            system_instruction=(
                "You are a precise data extraction agent. Extract ONLY data that is "
                "explicitly present in the provided tables. Never fabricate or infer values. "
                "For each value, it must be directly traceable to the source table."
            ),
            task_description="Table data extraction",
            temperature=0.1,
        )

        return result.get("records", [])

    def _extract_from_text(
        self,
        parsed_doc: ParsedDocument,
        schema: ExtractionSchema,
    ) -> list[dict]:
        """Extract data from text sections using Gemini."""
        # Build focused text from relevant sections
        doc_markdown = parsed_doc.to_markdown()
        
        # Truncate if too long (Gemini Flash handles ~1M tokens, but let's be practical)
        if len(doc_markdown) > 50000:
            doc_markdown = doc_markdown[:50000] + "\n\n[... document truncated ...]"

        prompt = f"""{schema.to_prompt_description()}

Below is the parsed content of the research paper "{parsed_doc.filename}".
Extract all records that match the schema from this text.

For the "source_location" field, specify the section name and page number where the data was found.
If a field value is not explicitly stated, use null.
Only extract data that is explicitly present — do NOT infer or hallucinate values.

DOCUMENT CONTENT:
{doc_markdown}

Return a JSON object with a "records" key containing an array of extracted records.
Each record should have the schema fields as keys.
If no matching data is found, return {{"records": []}}.
"""

        result = self.call_llm_json(
            prompt=prompt,
            system_instruction=(
                "You are a precise data extraction agent working on a research paper. "
                "Extract ONLY information that is explicitly stated in the text. "
                "For numerical values, preserve exact formatting (e.g., '95.2%', '±0.3'). "
                "Never fabricate, guess, or infer values that aren't directly in the text. "
                "Always cite the specific section or page where each value was found."
            ),
            task_description="Text content extraction",
            temperature=0.1,
        )

        return result.get("records", [])

    def _merge_records(
        self,
        table_records: list[dict],
        text_records: list[dict],
        schema: ExtractionSchema,
    ) -> list[dict]:
        """Merge records from tables and text, avoiding duplicates."""
        if not table_records:
            return text_records
        if not text_records:
            return table_records

        # Use key fields to detect duplicates
        key_fields = [f.name for f in schema.fields if f.required][:2]
        
        merged = list(table_records)
        existing_keys = set()
        
        for rec in table_records:
            key = tuple(str(rec.get(f, "")).lower().strip() for f in key_fields)
            existing_keys.add(key)

        for rec in text_records:
            key = tuple(str(rec.get(f, "")).lower().strip() for f in key_fields)
            if key not in existing_keys:
                merged.append(rec)
                existing_keys.add(key)

        return merged
