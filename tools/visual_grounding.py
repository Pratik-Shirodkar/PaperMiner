"""
Visual Grounding Tool — Highlights exact source evidence directly on PDF page images.
Provides visual proof of groundedness with colored bounding boxes.
"""

import re
import io
import pymupdf as fitz
from typing import Optional


def render_page_with_highlights(
    pdf_path: str,
    page_number: int,
    keywords_to_highlight: list[str],
    zoom: float = 2.0,
) -> Optional[bytes]:
    """
    Render a specific PDF page with bounding boxes around matching keywords.
    Returns PNG image bytes.
    """
    try:
        doc = fitz.open(pdf_path)
        if page_number < 1 or page_number > len(doc):
            doc.close()
            return None

        page = doc[page_number - 1]

        # Draw highlight rects
        for kw in keywords_to_highlight:
            if not kw or len(str(kw).strip()) < 2:
                continue

            # Clean search term
            clean_kw = str(kw).strip()
            # Try exact search
            rects = page.search_for(clean_kw)
            
            # If not found, try searching for first couple words
            if not rects and " " in clean_kw:
                first_part = clean_kw.split()[0]
                if len(first_part) > 2:
                    rects = page.search_for(first_part)

            for rect in rects[:10]:
                # Draw translucent bounding box with neon accent border
                page.draw_rect(
                    rect,
                    color=(0.52, 0.98, 0.69),  # Mint green border
                    fill=(0.52, 0.98, 0.69),   # Mint green fill
                    fill_opacity=0.25,
                    width=2,
                )

        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        doc.close()
        return img_bytes

    except Exception:
        return None


def extract_page_number_from_citation(source_location: str) -> int:
    """Extract integer page number from citations like 'Table 2, Section 6.1, page 8'."""
    if not source_location:
        return 1

    match = re.search(r'page\s*(\d+)', source_location, re.IGNORECASE)
    if match:
        return int(match.group(1))

    match = re.search(r'p\.?\s*(\d+)', source_location, re.IGNORECASE)
    if match:
        return int(match.group(1))

    return 1
