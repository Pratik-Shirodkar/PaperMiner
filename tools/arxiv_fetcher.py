"""
arXiv Auto-Ingest Tool — Fetch papers directly via ID, URL, or keyword search.
Enables 1-click zero-friction testing for judges and researchers.
"""

import os
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional


def normalize_arxiv_id(query: str) -> Optional[str]:
    """Extract clean arXiv ID from URL or raw ID string."""
    query = query.strip()

    # Matches https://arxiv.org/abs/1706.03762 or https://arxiv.org/pdf/1706.03762.pdf
    url_match = re.search(r'arxiv\.org\/(?:abs|pdf)\/(\d+\.\d+(?:v\d+)?)', query, re.IGNORECASE)
    if url_match:
        return url_match.group(1)

    # Matches 1706.03762 or 1706.03762v7
    id_match = re.match(r'^(\d{4}\.\d{4,5}(?:v\d+)?)$', query)
    if id_match:
        return id_match.group(1)

    return None


def fetch_arxiv_pdf(arxiv_id: str, dest_dir: str = "sample_papers") -> tuple[str, dict]:
    """
    Download an arXiv paper by ID and fetch its metadata.
    Returns (local_pdf_path, metadata_dict).
    """
    clean_id = normalize_arxiv_id(arxiv_id) or arxiv_id
    pdf_url = f"https://arxiv.org/pdf/{clean_id}.pdf"
    
    # Clean file name
    clean_filename = f"arxiv_{clean_id.replace('/', '_')}.pdf"
    dest_path = Path(dest_dir) / clean_filename
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Download PDF
    req = urllib.request.Request(
        pdf_url,
        headers={"User-Agent": "PaperMiner-Research-Agent/1.0"}
    )
    with urllib.request.urlopen(req) as response, open(dest_path, "wb") as out_file:
        out_file.write(response.read())

    # Fetch metadata via arXiv API
    meta = fetch_arxiv_metadata(clean_id)

    return str(dest_path), meta


def fetch_arxiv_metadata(arxiv_id: str) -> dict:
    """Fetch title, authors, summary from arXiv API."""
    api_url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "PaperMiner/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.find("atom:entry", ns)
        if entry is not None:
            title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
            summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
            authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]
            published = entry.find("atom:published", ns).text[:10]
            return {
                "arxiv_id": arxiv_id,
                "title": title,
                "authors": authors,
                "summary": summary,
                "published": published,
            }
    except Exception:
        pass
    return {"arxiv_id": arxiv_id, "title": f"arXiv:{arxiv_id}", "authors": [], "summary": ""}


def search_arxiv(query: str, max_results: int = 5) -> list[dict]:
    """Search arXiv by keyword and return top matches."""
    encoded_query = urllib.parse.quote(query)
    api_url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_query}&max_results={max_results}&sortBy=relevance"
    
    results = []
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "PaperMiner/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        
        for entry in root.findall("atom:entry", ns):
            arxiv_id_elem = entry.find("atom:id", ns)
            if arxiv_id_elem is None:
                continue
            raw_id = arxiv_id_elem.text.split("/abs/")[-1]
            title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
            summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")[:250] + "..."
            authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]
            
            results.append({
                "arxiv_id": raw_id,
                "title": title,
                "authors": ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else ""),
                "summary": summary,
            })
    except Exception:
        pass
    return results
