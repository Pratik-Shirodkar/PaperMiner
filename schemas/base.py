"""
Base schema definitions for structured data extraction.
Uses Pydantic v2 for type-safe, validated extraction targets.
"""

from typing import Any, Optional, Union
from pydantic import BaseModel, Field, field_validator


class SchemaField(BaseModel):
    """Definition of a single field to extract."""
    name: str = Field(description="Field name / column header")
    field_type: str = Field(description="Expected type: string, number, boolean, list")
    description: str = Field(description="What this field represents — guides the AI extractor")
    required: bool = Field(default=True, description="Whether this field must be present")
    examples: list[str] = Field(default_factory=list, description="Example values to guide extraction")

    @field_validator("examples", mode="before")
    @classmethod
    def coerce_examples_to_strings(cls, v: Any) -> list[str]:
        if not v:
            return []
        if isinstance(v, str):
            return [v]
        cleaned = []
        if isinstance(v, (list, tuple)):
            for item in v:
                if isinstance(item, list):
                    cleaned.extend([str(sub) for sub in item if sub is not None])
                elif item is not None:
                    cleaned.append(str(item))
        return cleaned[:5]


class ExtractionSchema(BaseModel):
    """Schema defining what to extract from a document."""
    name: str = Field(description="Schema name, e.g. 'ML Benchmark Results'")
    description: str = Field(description="What kind of data this schema captures")
    fields: list[SchemaField] = Field(description="Fields to extract per record")
    expects_multiple: bool = Field(
        default=True,
        description="True if multiple records expected (e.g., multiple experiments)"
    )

    def to_prompt_description(self) -> str:
        """Convert schema to a natural language description for the LLM."""
        lines = [
            f"Extract data matching the schema: **{self.name}**",
            f"Description: {self.description}",
            "",
            "Fields to extract for each record:",
        ]
        for f in self.fields:
            req = "REQUIRED" if f.required else "optional"
            examples_str = f" (examples: {', '.join(f.examples)})" if f.examples else ""
            lines.append(f"  - **{f.name}** ({f.field_type}, {req}): {f.description}{examples_str}")

        if self.expects_multiple:
            lines.append("\nExtract ALL matching records found in the document.")
        else:
            lines.append("\nExtract a single record from the document.")

        return "\n".join(lines)

    def get_json_structure(self) -> dict:
        """Get the expected JSON structure for one record."""
        structure = {}
        for f in self.fields:
            if f.field_type == "number":
                structure[f.name] = 0.0
            elif f.field_type == "boolean":
                structure[f.name] = False
            elif f.field_type == "list":
                structure[f.name] = []
            else:
                structure[f.name] = ""
        return structure
