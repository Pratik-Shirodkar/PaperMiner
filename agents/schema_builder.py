"""
Schema Builder — Uses Gemini to generate extraction schemas
from natural language descriptions.
"""

import json
from typing import Optional

from agents.base import BaseAgent
from schemas.base import ExtractionSchema, SchemaField
from utils.cost_tracker import CostTracker


class SchemaBuilderAgent(BaseAgent):
    """
    Generates custom Pydantic extraction schemas from natural language descriptions.

    Examples:
    - "Extract all gene names and their associated diseases"
    - "Get model names, accuracy scores, and training datasets"
    - "Find drug dosages, patient outcomes, and side effects"
    """

    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        super().__init__(
            name="Schema Builder",
            role="Schema generation specialist. You convert natural language descriptions "
                 "of desired data into structured extraction schemas.",
            cost_tracker=cost_tracker,
        )

    def build_schema(self, description: str) -> ExtractionSchema:
        """
        Build an ExtractionSchema from a natural language description.

        Args:
            description: e.g. "extract all gene names and their associated diseases"

        Returns:
            A fully formed ExtractionSchema ready for the Extractor Agent
        """
        self.send_message(
            receiver="Orchestrator",
            message_type="status",
            content=f"Building custom schema from: '{description}'",
        )

        prompt = f"""Create a structured data extraction schema based on this description:

"{description}"

Generate a JSON object with:
{{
  "name": "Short schema name (e.g. 'Gene-Disease Associations')",
  "description": "One-sentence description of what this schema extracts",
  "expects_multiple": true,
  "fields": [
    {{
      "name": "field_name_snake_case",
      "field_type": "string|number|boolean|list",
      "description": "What this field represents - be specific to guide the AI extractor",
      "required": true/false,
      "examples": ["example_value_1", "example_value_2"]
    }}
  ]
}}

Rules:
- Include 3-8 fields (not too many, not too few)
- Always include a "source_location" field (where in the paper this was found)
- Use snake_case for field names
- Field types: "string" for text, "number" for pure numbers, "list" for arrays
- Mark the most important fields as required=true
- Provide 2-3 realistic examples per field
"""

        result = self.call_llm_json(
            prompt=prompt,
            system_instruction=(
                "You are a schema design expert. Create precise, well-structured "
                "extraction schemas. Field descriptions should be specific enough to "
                "guide an AI to extract the right data from a research paper."
            ),
            task_description="Custom schema generation",
        )

        # Build the ExtractionSchema from the LLM response
        fields = []
        for f in result.get("fields", []):
            raw_ex = f.get("examples", [])
            clean_ex = self._clean_examples_list(raw_ex)
            fields.append(SchemaField(
                name=str(f.get("name", "unnamed")).strip().lower().replace(" ", "_"),
                field_type=f.get("field_type", "string"),
                description=f.get("description", ""),
                required=f.get("required", True),
                examples=clean_ex,
            ))

        # Ensure source_location field exists
        field_names = [f.name for f in fields]
        if "source_location" not in field_names:
            fields.append(SchemaField(
                name="source_location",
                field_type="string",
                description="Where in the paper this data was found (section, table, page)",
                required=True,
                examples=["Table 1", "Section 3.2, page 5"],
            ))

        schema = ExtractionSchema(
            name=result.get("name", "Custom Schema"),
            description=result.get("description", description),
            fields=fields,
            expects_multiple=result.get("expects_multiple", True),
        )

        self.send_message(
            receiver="Orchestrator",
            message_type="response",
            content={
                "status": "success",
                "schema_name": schema.name,
                "field_count": len(schema.fields),
            },
        )

        return schema

    def detect_and_build_schema_for_doc(self, doc_text: str, filename: str = "") -> ExtractionSchema:
        """
        Analyze a research paper and automatically design the optimal extraction schema.
        Handles medical, clinical, materials science, chemistry, ML, biology, physics, etc.
        """
        self.send_message(
            receiver="Orchestrator",
            message_type="status",
            content=f"Auto-detecting optimal schema for: {filename or 'document'}",
        )

        sample = doc_text[:5000]

        prompt = f"""You are a scientific research data architect. Analyze this research paper sample and design the optimal structured data extraction schema.

DOCUMENT SAMPLE ({filename}):
---
{sample}
---

Identify what this paper's core experimental or empirical findings are (e.g. clinical trial outcomes, patient cohort results, biomarker associations, material constants, model benchmarks, chemical synthesis yields, etc.).

Design a schema with 4 to 8 fields to extract ALL core data records from this paper.

Return a JSON object:
{{
  "name": "Specific Schema Name (e.g. 'Clinical Trial & Patient Outcomes' or 'Cardiology Cohort Findings')",
  "description": "Specific description of what will be extracted",
  "fields": [
    {{
      "name": "field_name_snake_case",
      "field_type": "string",
      "description": "What this field captures",
      "required": true,
      "examples": ["example1", "example2"]
    }}
  ]
}}

Always include a "source_location" field for citation.
"""
        result = self.call_llm_json(
            prompt=prompt,
            system_instruction="You are an expert at identifying the key data points in scientific literature across medicine, biology, ML, physics, and chemistry.",
            task_description="Auto-detect schema from document",
        )

        fields = []
        for f in result.get("fields", []):
            raw_ex = f.get("examples", [])
            clean_ex = self._clean_examples_list(raw_ex)
            fields.append(SchemaField(
                name=str(f.get("name", "unnamed")).strip().lower().replace(" ", "_"),
                field_type=f.get("field_type", "string"),
                description=f.get("description", ""),
                required=f.get("required", True),
                examples=clean_ex,
            ))

        field_names = [f.name for f in fields]
        if "source_location" not in field_names:
            fields.append(SchemaField(
                name="source_location",
                field_type="string",
                description="Where in the paper this data was found (section, table, page)",
                required=True,
                examples=["Table 1", "Section 3.2"],
            ))

        schema = ExtractionSchema(
            name=result.get("name", "Auto-Detected Schema"),
            description=result.get("description", "Auto-generated based on document content"),
            fields=fields,
            expects_multiple=True,
        )

        self.send_message(
            receiver="Orchestrator",
            message_type="response",
            content={
                "status": "success",
                "schema_name": schema.name,
                "field_count": len(schema.fields),
            },
        )

        return schema

    @staticmethod
    def _clean_examples_list(raw_examples) -> list[str]:
        """Flatten and sanitize arbitrary LLM example values into clean strings."""
        if not raw_examples:
            return []
        if isinstance(raw_examples, str):
            return [raw_examples]
        cleaned = []
        if isinstance(raw_examples, (list, tuple)):
            for item in raw_examples:
                if isinstance(item, list):
                    cleaned.extend([str(sub).strip() for sub in item if sub is not None])
                elif isinstance(item, dict):
                    cleaned.append(json.dumps(item))
                elif item is not None:
                    cleaned.append(str(item).strip())
        return [c for c in cleaned if c][:5]


