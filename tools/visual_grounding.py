"""
Visual Grounding Tool — Highlights exact source evidence directly on PDF page images.
Provides visual proof of groundedness with colored bounding boxes.
"""

import re
import io
import pymupdf as fitz
from typing import Optional, Union


def render_page_with_highlights(
    pdf_path: str,
    page_number: int,
    keywords_to_highlight: list[str],
    zoom: float = 2.0,
) -> Optional[bytes]:
    """
    Render a specific PDF page with bounding boxes around matching keywords.
    Automatically handles journal/book pagination offsets by searching document pages.
    Returns PNG image bytes.
    """
    try:
        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            doc.close()
            return None

        # Clean and prepare keywords
        clean_kws = [str(kw).strip() for kw in keywords_to_highlight if kw and len(str(kw).strip()) >= 2]

        target_page_idx = -1

        # If page_number is valid for this PDF, check if keywords match there
        if 1 <= page_number <= len(doc):
            target_page_idx = page_number - 1
        else:
            # If citation has journal pagination (e.g. p. 299 in a 10-page PDF),
            # search across all pages in the PDF for matching keywords
            best_match_idx = 0
            max_matches = 0

            for p_idx in range(len(doc)):
                p = doc[p_idx]
                matches = 0
                for kw in clean_kws:
                    if p.search_for(kw):
                        matches += 2
                    elif " " in kw and p.search_for(kw.split()[0]):
                        matches += 1
                if matches > max_matches:
                    max_matches = matches
                    best_match_idx = p_idx

            target_page_idx = best_match_idx

        page = doc[target_page_idx]

        # Draw highlight rects
        for kw in clean_kws:
            # Try exact search
            rects = page.search_for(kw)
            
            # If not found, try searching for first couple words
            if not rects and " " in kw:
                first_part = kw.split()[0]
                if len(first_part) > 2:
                    rects = page.search_for(first_part)

            for rect in rects[:10]:
                # Draw translucent bounding box with neon accent border
                page.draw_rect(
                    rect,
                    color=(0.31, 0.27, 0.90),  # Indigo border (#4F46E5)
                    fill=(0.20, 0.83, 0.60),   # Mint green translucent fill
                    fill_opacity=0.28,
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

    # Search for standalone numbers after 'Table X' or section
    match = re.search(r'\b(\d{1,4})\b', source_location)
    if match:
        return int(match.group(1))

    return 1
