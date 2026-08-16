"""
PDF processing tools using PyMuPDF and pdfplumber.
Handles text extraction, table detection, section splitting, and figure captions.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pymupdf as fitz
import pdfplumber


@dataclass
class ExtractedTable:
    """A table extracted from a PDF page."""
    page_number: int
    table_index: int
    headers: list[str]
    rows: list[list[str]]
    caption: str = ""

    def to_markdown(self) -> str:
        """Convert table to markdown format."""
        if not self.headers and not self.rows:
            return ""

        # Use headers if available, else generate column names
        headers = self.headers if self.headers else [f"Col_{i+1}" for i in range(len(self.rows[0]))]
        
        lines = []
        if self.caption:
            lines.append(f"**{self.caption}**\n")
        
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in self.rows:
            # Pad or trim row to match header count
            padded = row + [""] * (len(headers) - len(row))
            lines.append("| " + " | ".join(padded[:len(headers)]) + " |")
        
        return "\n".join(lines)


@dataclass
class DocumentSection:
    """A logical section of the document."""
    title: str
    level: int  # heading level (1, 2, 3)
    content: str
    page_start: int
    page_end: int
    tables: list[ExtractedTable] = field(default_factory=list)


@dataclass
class ParsedDocument:
    """Complete parsed representation of a PDF document."""
    filename: str
    total_pages: int
    full_text: str
    sections: list[DocumentSection]
    tables: list[ExtractedTable]
    figure_captions: list[str]
    metadata: dict = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Convert the entire parsed document to a structured markdown string."""
        parts = []
        parts.append(f"# Document: {self.filename}")
        parts.append(f"**Pages:** {self.total_pages}\n")

        if self.metadata:
            parts.append("## Document Metadata")
            for key, value in self.metadata.items():
                parts.append(f"- **{key}:** {value}")
            parts.append("")

        for section in self.sections:
            heading_prefix = "#" * min(section.level + 1, 4)
            parts.append(f"{heading_prefix} {section.title}")
            parts.append(f"*(Pages {section.page_start}–{section.page_end})*\n")
            parts.append(section.content)
            
            for table in section.tables:
                parts.append(f"\n{table.to_markdown()}\n")
            parts.append("")

        if self.tables:
            # Include any tables not assigned to sections
            unassigned = [t for t in self.tables if not any(
                t in s.tables for s in self.sections
            )]
            if unassigned:
                parts.append("## Additional Tables")
                for table in unassigned:
                    parts.append(f"\n*Table from page {table.page_number}:*")
                    parts.append(table.to_markdown())
                    parts.append("")

        if self.figure_captions:
            parts.append("## Figure Captions")
            for i, caption in enumerate(self.figure_captions, 1):
                parts.append(f"{i}. {caption}")
            parts.append("")

        return "\n".join(parts)


def extract_text_pymupdf(pdf_path: str) -> tuple[str, int, dict]:
    """Extract full text and metadata using PyMuPDF."""
    doc = fitz.open(pdf_path)
    pages_text = []
    for page in doc:
        pages_text.append(page.get_text("text"))

    metadata = {}
    if doc.metadata:
        for key in ["title", "author", "subject", "keywords"]:
            if doc.metadata.get(key):
                metadata[key] = doc.metadata[key]

    total_pages = len(doc)
    full_text = "\n\n".join(pages_text)
    doc.close()
    return full_text, total_pages, metadata


def extract_tables_pdfplumber(pdf_path: str) -> list[ExtractedTable]:
    """Extract tables using pdfplumber's table detection."""
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            page_tables = page.extract_tables()
            if not page_tables:
                continue
            
            # Also get page text for caption detection
            page_text = page.extract_text() or ""
            
            for idx, table_data in enumerate(page_tables):
                if not table_data or len(table_data) < 2:
                    continue

                # First row as headers, rest as data
                raw_headers = table_data[0]
                headers = [str(h).strip() if h else "" for h in raw_headers]
                rows = []
                for row in table_data[1:]:
                    cleaned = [str(cell).strip() if cell else "" for cell in row]
                    if any(cleaned):  # Skip fully empty rows
                        rows.append(cleaned)

                # Try to find a caption near the table
                caption = _find_table_caption(page_text, idx)

                tables.append(ExtractedTable(
                    page_number=page_num,
                    table_index=idx,
                    headers=headers,
                    rows=rows,
                    caption=caption,
                ))
    return tables


def _find_table_caption(page_text: str, table_index: int) -> str:
    """Try to extract table caption from page text."""
    patterns = [
        r'(Table\s+\d+[\.:]\s*[^\n]+)',
        r'(TABLE\s+\d+[\.:]\s*[^\n]+)',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, page_text)
        if matches and table_index < len(matches):
            return matches[table_index].strip()
    return ""


def extract_figure_captions(full_text: str) -> list[str]:
    """Extract figure captions from the document text."""
    patterns = [
        r'(Fig(?:ure)?\.?\s+\d+[\.:]\s*[^\n]+(?:\n(?![A-Z\d])[^\n]+)*)',
        r'(FIGURE\s+\d+[\.:]\s*[^\n]+)',
    ]
    captions = []
    for pattern in patterns:
        matches = re.findall(pattern, full_text)
        for m in matches:
            caption = " ".join(m.strip().split())
            if caption not in captions:
                captions.append(caption)
    return captions


# Common section heading patterns in research papers
SECTION_PATTERNS = [
    r'^(?:(\d+\.?\s+)?)(Abstract)\s*$',
    r'^(?:(\d+\.?\s+)?)(Introduction)\s*$',
    r'^(?:(\d+\.?\s+)?)(Related\s+Work)\s*$',
    r'^(?:(\d+\.?\s+)?)(Background)\s*$',
    r'^(?:(\d+\.?\s+)?)(Methodology|Methods?)\s*$',
    r'^(?:(\d+\.?\s+)?)(Experiments?|Experimental\s+Setup)\s*$',
    r'^(?:(\d+\.?\s+)?)(Results?(?:\s+and\s+Discussion)?)\s*$',
    r'^(?:(\d+\.?\s+)?)(Discussion)\s*$',
    r'^(?:(\d+\.?\s+)?)(Conclusion|Conclusions|Summary)\s*$',
    r'^(?:(\d+\.?\s+)?)(References|Bibliography)\s*$',
    r'^(?:(\d+\.?\s+)?)(Appendix|Appendices)\s*$',
    r'^(\d+\.)\s+([A-Z][A-Za-z\s&:,]+)$',  # Numbered sections like "1. Something"
    r'^(\d+\.\d+\.?)\s+([A-Z][A-Za-z\s&:,]+)$',  # Subsections like "1.1 Something"
]


def split_into_sections(full_text: str, total_pages: int) -> list[DocumentSection]:
    """Split document text into logical sections based on heading patterns."""
    lines = full_text.split("\n")
    sections: list[DocumentSection] = []
    current_title = "Preamble"
    current_content_lines: list[str] = []
    current_level = 1

    # Estimate page per line (rough)
    lines_per_page = max(len(lines) // max(total_pages, 1), 1)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            current_content_lines.append("")
            continue

        is_heading = False
        heading_title = stripped
        heading_level = 1

        for pattern in SECTION_PATTERNS:
            match = re.match(pattern, stripped, re.IGNORECASE)
            if match:
                groups = [g for g in match.groups() if g]
                heading_title = groups[-1].strip() if groups else stripped
                # Determine level from numbering
                if any(g and re.match(r'\d+\.\d+', g) for g in match.groups() if g):
                    heading_level = 2
                elif any(g and re.match(r'\d+\.', g) for g in match.groups() if g):
                    heading_level = 1
                is_heading = True
                break

        if is_heading and len(stripped) < 100:  # Headings shouldn't be too long
            # Save current section
            if current_content_lines or current_title != "Preamble":
                page_start = max(1, (i - len(current_content_lines)) // lines_per_page + 1)
                page_end = min(total_pages, i // lines_per_page + 1)
                sections.append(DocumentSection(
                    title=current_title,
                    level=current_level,
                    content="\n".join(current_content_lines).strip(),
                    page_start=page_start,
                    page_end=page_end,
                ))
            current_title = heading_title
            current_level = heading_level
            current_content_lines = []
        else:
            current_content_lines.append(line)

    # Don't forget the last section
    if current_content_lines:
        page_start = max(1, (len(lines) - len(current_content_lines)) // lines_per_page + 1)
        sections.append(DocumentSection(
            title=current_title,
            level=current_level,
            content="\n".join(current_content_lines).strip(),
            page_start=page_start,
            page_end=total_pages,
        ))

    return sections


def parse_pdf(pdf_path: str) -> ParsedDocument:
    """Full PDF parsing pipeline — the main entry point."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if not path.suffix.lower() == ".pdf":
        raise ValueError(f"Not a PDF file: {pdf_path}")

    # Step 1: Extract raw text and metadata
    full_text, total_pages, metadata = extract_text_pymupdf(pdf_path)

    # Step 2: Extract tables
    tables = extract_tables_pdfplumber(pdf_path)

    # Step 3: Extract figure captions
    figure_captions = extract_figure_captions(full_text)

    # Step 4: Split into sections
    sections = split_into_sections(full_text, total_pages)

    # Step 5: Assign tables to sections by page number
    for table in tables:
        for section in sections:
            if section.page_start <= table.page_number <= section.page_end:
                section.tables.append(table)
                break

    return ParsedDocument(
        filename=path.name,
        total_pages=total_pages,
        full_text=full_text,
        sections=sections,
        tables=tables,
        figure_captions=figure_captions,
        metadata=metadata,
    )
