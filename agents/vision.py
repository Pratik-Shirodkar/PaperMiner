"""
Vision Agent — Uses Gemini's multimodal vision to extract data from
figures, charts, and image-based tables that text parsers can't handle.
"""

import base64
from pathlib import Path
from typing import Optional

import pymupdf as fitz

from agents.base import BaseAgent
from utils.cost_tracker import CostTracker


class VisionAgent(BaseAgent):
    """
    Extracts data from figures, charts, and image-based tables using
    Gemini's multimodal vision capabilities.

    Key capabilities:
    - Renders PDF pages to images and sends to Gemini Vision
    - Reads bar charts, scatter plots, line graphs
    - Handles image-based tables (scanned / non-selectable text)
    - Extracts data points with axis labels and legends
    """

    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        super().__init__(
            name="Vision Agent",
            role="Multimodal figure and chart reader. You analyze images of scientific "
                 "figures, bar charts, scatter plots, and image-based tables to extract "
                 "structured numerical data.",
            cost_tracker=cost_tracker,
        )

    def extract_from_figures(
        self,
        pdf_path: str,
        schema_description: str,
        page_numbers: list[int] | None = None,
    ) -> list[dict]:
        """
        Render PDF pages to images and extract figure/chart data via Gemini Vision.

        Args:
            pdf_path: Path to the PDF
            schema_description: Description of what data to extract
            page_numbers: Specific pages to analyze (None = auto-detect figure pages)

        Returns:
            List of extracted records from figures
        """
        self.send_message(
            receiver="Orchestrator",
            message_type="status",
            content="Starting visual figure/chart extraction...",
        )

        doc = fitz.open(pdf_path)
        pages_to_scan = page_numbers or self._detect_figure_pages(doc)

        if not pages_to_scan:
            self.send_message(
                receiver="Orchestrator",
                message_type="response",
                content={"status": "success", "records": 0, "note": "No figure pages detected"},
            )
            doc.close()
            return []

        all_records: list[dict] = []

        for page_num in pages_to_scan:
            if page_num < 1 or page_num > len(doc):
                continue

            page = doc[page_num - 1]  # fitz is 0-indexed

            # Render page to a high-res PNG image
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for clarity
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")

            records = self._analyze_page_image(img_b64, page_num, schema_description)
            all_records.extend(records)

        doc.close()

        self.send_message(
            receiver="Orchestrator",
            message_type="response",
            content={
                "status": "success",
                "records": len(all_records),
                "pages_scanned": len(pages_to_scan),
            },
        )

        return all_records

    def _detect_figure_pages(self, doc: fitz.Document) -> list[int]:
        """Auto-detect pages likely containing figures or charts."""
        figure_pages = []
        for page_num, page in enumerate(doc, 1):
            text = page.get_text("text").lower()
            images = page.get_images(full=True)

            # Heuristics: page has images AND figure-related text
            has_figure_text = any(kw in text for kw in [
                "figure", "fig.", "chart", "plot", "graph",
                "histogram", "scatter", "bar chart",
            ])
            has_substantial_images = len(images) > 0

            if has_figure_text and has_substantial_images:
                figure_pages.append(page_num)

        return figure_pages[:5]  # Cap at 5 pages to control costs

    def _analyze_page_image(
        self,
        img_b64: str,
        page_num: int,
        schema_description: str,
    ) -> list[dict]:
        """Send a page image to Gemini Vision for data extraction."""
        from google.genai import types

        prompt = f"""Analyze this research paper page image and extract any numerical data from:
- Bar charts, line graphs, scatter plots
- Image-based tables (where text is embedded in the image)
- Any other visual data representations

{schema_description}

For each data point or record you find, include:
- The figure/chart identifier (e.g., "Figure 3")
- All extracted values with labels
- The source description (e.g., "Figure 3, bar chart, x-axis: Model, y-axis: Accuracy")

Return a JSON object: {{"records": [...]}}
Each record should have descriptive field names based on what you see.
If the page has no extractable figures or charts, return {{"records": []}}.
"""
        try:
            config = types.GenerateContentConfig(
                temperature=0.1,
                system_instruction=(
                    "You are a specialist at reading scientific figures and charts. "
                    "Extract precise numerical values from visual representations. "
                    "Always specify units and axis labels. If a value is approximate "
                    "from a bar/line chart, indicate it with '~' prefix."
                ),
                response_mime_type="application/json",
            )

            # Build multimodal content with inline image data
            contents = [
                types.Part.from_bytes(data=base64.b64decode(img_b64), mime_type="image/png"),
                types.Part.from_text(text=prompt),
            ]

            import time
            start = time.time()

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )

            duration = time.time() - start

            input_tokens = response.usage_metadata.prompt_token_count or 0
            output_tokens = response.usage_metadata.candidates_token_count or 0
            self.cost_tracker.record_call(
                agent_name=self.name,
                task_description=f"Vision analysis page {page_num}",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_seconds=duration,
            )

            import json
            result = json.loads(response.text or '{"records": []}')
            records = result.get("records", [])

            # Tag each record with source
            for rec in records:
                rec["source_location"] = rec.get("source_location", f"Figure on page {page_num} (vision)")

            return records

        except Exception as e:
            self.send_message(
                receiver="Orchestrator",
                message_type="error",
                content=f"Vision extraction failed on page {page_num}: {str(e)}",
            )
            return []
