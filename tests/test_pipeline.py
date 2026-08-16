"""
Automated unit and integration tests for PaperMiner components.
Run with: python -m pytest tests/ -v
"""

import os
import json
import pytest
from pathlib import Path

from schemas.base import ExtractionSchema, SchemaField
from schemas.presets import PRESET_SCHEMAS, get_schema, list_schemas
from tools.pdf_tools import parse_pdf, ParsedDocument
from tools.export_tools import to_json, to_csv, to_excel, to_latex, to_audit_report
from utils.cost_tracker import CostTracker


# ─── SCHEMA TESTS ───

def test_preset_schemas_exist():
    """Verify all 4 preset schemas are registered and valid."""
    assert len(PRESET_SCHEMAS) >= 4
    for key, schema in PRESET_SCHEMAS.items():
        assert isinstance(schema, ExtractionSchema)
        assert len(schema.fields) >= 4
        assert schema.name
        # Every schema must have a source_location field
        field_names = [f.name for f in schema.fields]
        assert "source_location" in field_names


def test_schema_prompt_generation():
    """Test schema prompt conversion."""
    schema = get_schema("ml_benchmarks")
    prompt = schema.to_prompt_description()
    assert "ML Benchmark Results" in prompt
    assert "model_name" in prompt
    assert "score" in prompt


# ─── EXPORT TOOLS TESTS ───

@pytest.fixture
def sample_extractions():
    return [
        {
            "model_name": "Transformer (big)",
            "dataset": "WMT 2014 En-De",
            "metric": "BLEU",
            "score": "28.4",
            "parameters": "213M",
            "training_details": "8x P100 GPUs",
            "source_location": "Table 2, page 8",
        },
        {
            "model_name": "ConvS2S",
            "dataset": "WMT 2014 En-De",
            "metric": "BLEU",
            "score": "25.16",
            "parameters": "Unknown",
            "training_details": "K40 GPUs",
            "source_location": "Table 2, page 8",
        },
    ]


@pytest.fixture
def sample_validations():
    return [
        {
            "record_index": 0,
            "overall_confidence": "HIGH",
            "issues": [],
            "corrections": [],
        },
        {
            "record_index": 1,
            "overall_confidence": "HIGH",
            "issues": [],
            "corrections": [],
        },
    ]


def test_export_to_json(sample_extractions, sample_validations):
    json_str = to_json(sample_extractions, sample_validations)
    data = json.loads(json_str)
    assert data["total_records"] == 2
    assert len(data["records"]) == 2
    assert data["records"][0]["model_name"] == "Transformer (big)"
    assert data["records"][0]["_validation"]["overall_confidence"] == "HIGH"


def test_export_to_csv(sample_extractions):
    csv_str = to_csv(sample_extractions)
    lines = csv_str.strip().split("\n")
    assert len(lines) == 3  # Header + 2 rows
    assert "model_name" in lines[0]
    assert "Transformer (big)" in lines[1]


def test_export_to_excel(sample_extractions):
    xlsx_bytes = to_excel(sample_extractions)
    assert isinstance(xlsx_bytes, bytes)
    assert len(xlsx_bytes) > 1000  # Valid binary Excel file


def test_export_to_latex(sample_extractions):
    latex_str = to_latex(sample_extractions)
    assert "\\begin{table}" in latex_str
    assert "\\end{table}" in latex_str
    assert "Transformer (big)" in latex_str
    assert "\\textbf{model\\_name}" in latex_str


def test_export_to_audit_report(sample_extractions, sample_validations):
    cost_report = "Total Cost: $0.014"
    log = [{"sender": "Orchestrator", "receiver": "Parser Agent", "type": "request"}]
    audit = to_audit_report("test.pdf", sample_extractions, sample_validations, log, cost_report)
    assert "# PaperMiner Audit Report" in audit
    assert "HIGH confidence: 2" in audit
    assert "Transformer (big)" in audit
    assert "Orchestrator" in audit


# ─── COST TRACKER TESTS ───

def test_cost_tracker():
    tracker = CostTracker()
    tracker.record_call(
        agent_name="Extractor Agent",
        task_description="Test extraction",
        input_tokens=10000,
        output_tokens=2000,
        duration_seconds=5.0,
    )
    assert tracker.total_input_tokens == 10000
    assert tracker.total_output_tokens == 2000
    assert tracker.total_cost_usd > 0
    report = tracker.format_report()
    assert "Extractor Agent" in report
    assert "TOTAL COST" in report


# ─── PDF PARSING TESTS ───

def test_pdf_parsing_sample():
    sample_pdf = Path("sample_papers/attention_is_all_you_need.pdf")
    if sample_pdf.exists():
        doc = parse_pdf(str(sample_pdf))
        assert doc.total_pages == 15
        assert len(doc.tables) >= 5
        assert len(doc.sections) >= 5
        markdown = doc.to_markdown()
        assert len(markdown) > 1000


# ─── NEW FEATURE TESTS ───

def test_arxiv_id_normalization():
    from tools.arxiv_fetcher import normalize_arxiv_id
    assert normalize_arxiv_id("https://arxiv.org/abs/1706.03762") == "1706.03762"
    assert normalize_arxiv_id("https://arxiv.org/pdf/1706.03762v7.pdf") == "1706.03762v7"
    assert normalize_arxiv_id("1706.03762") == "1706.03762"


def test_meta_analysis_chart_generation(sample_extractions):
    from tools.meta_analysis import generate_interactive_charts
    charts = generate_interactive_charts(sample_extractions, "ml_benchmarks")
    assert len(charts) >= 1
    assert "Benchmark" in charts[0]["title"]


def test_visual_grounding_rendering():
    from tools.visual_grounding import render_page_with_highlights, extract_page_number_from_citation
    assert extract_page_number_from_citation("Table 2, Section 6.1, page 8") == 8
    assert extract_page_number_from_citation("p. 12") == 12

    sample_pdf = Path("sample_papers/attention_is_all_you_need.pdf")
    if sample_pdf.exists():
        img = render_page_with_highlights(str(sample_pdf), 8, ["Transformer", "BLEU", "28.4"])
        assert isinstance(img, bytes)
        assert len(img) > 5000

