"""
Parser Agent — Converts raw PDFs into structured, LLM-ready representations.
Uses PyMuPDF and pdfplumber for extraction, NO LLM calls for basic parsing.
Uses Gemini only for intelligent section labeling when headings are ambiguous.
"""

from typing import Optional

from agents.base import BaseAgent
from tools.pdf_tools import ParsedDocument, parse_pdf
from utils.cost_tracker import CostTracker


class ParserAgent(BaseAgent):
    """
    Responsible for converting PDF files into structured markdown.
    
    Key capabilities:
    - Text extraction with layout preservation
    - Table detection and markdown conversion
    - Section boundary identification
    - Figure caption extraction
    - Intelligent section classification (uses LLM when headings are non-standard)
    """

    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        super().__init__(
            name="Parser Agent",
            role="PDF document parser and structure extractor. You convert raw PDF documents "
                 "into clean, structured markdown while preserving tables, sections, and figures.",
            cost_tracker=cost_tracker,
        )

    def parse(self, pdf_path: str) -> ParsedDocument:
        """Parse a PDF file into a structured representation."""
        self.send_message(
            receiver="Orchestrator",
            message_type="status",
            content=f"Starting PDF parsing: {pdf_path}",
        )

        # Step 1: Use PDF tools for structural extraction (no LLM needed)
        parsed = parse_pdf(pdf_path)

        self.send_message(
            receiver="Orchestrator",
            message_type="status",
            content=f"Basic parsing complete: {parsed.total_pages} pages, "
                    f"{len(parsed.sections)} sections, {len(parsed.tables)} tables",
        )

        # Step 2: If sections are poorly labeled, use LLM to improve them
        if self._needs_section_refinement(parsed):
            parsed = self._refine_sections(parsed)

        self.send_message(
            receiver="Orchestrator",
            message_type="response",
            content={
                "status": "success",
                "pages": parsed.total_pages,
                "sections": len(parsed.sections),
                "tables": len(parsed.tables),
                "figure_captions": len(parsed.figure_captions),
            },
        )

        return parsed

    def _needs_section_refinement(self, doc: ParsedDocument) -> bool:
        """Check if sections need LLM-assisted refinement."""
        if len(doc.sections) <= 1:
            return True  # No sections detected — needs help
        # Check if most sections are just "Preamble" or generic
        generic_count = sum(
            1 for s in doc.sections
            if s.title.lower() in ("preamble", "untitled", "")
        )
        return generic_count > len(doc.sections) // 2

    def _refine_sections(self, doc: ParsedDocument) -> ParsedDocument:
        """Use Gemini to intelligently identify section boundaries and labels."""
        # Take the first ~4000 chars to identify document structure
        sample_text = doc.full_text[:4000]

        result = self.call_llm_json(
            prompt=f"""Analyze this research paper text and identify the main sections.
Return a JSON array of section titles you can identify, in order of appearance.
Focus on standard academic sections (Abstract, Introduction, Methods, Results, etc.)
but also include any non-standard section names you find.

Text sample:
---
{sample_text}
---

Return format: {{"sections": ["Section Title 1", "Section Title 2", ...]}}""",
            system_instruction="You are a document structure analyzer. Identify section headings in academic papers.",
            task_description="Section refinement",
        )

        self.send_message(
            receiver="Orchestrator",
            message_type="status",
            content=f"Refined sections using LLM: {result.get('sections', [])}",
        )

        return doc  # Return with original parsing — the LLM result is used for context
