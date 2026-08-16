# ⛏️ PaperMiner

**Autonomous Multi-Agent Structured Data Extraction & Meta-Analysis Suite for Scientific Literature**

*Built for Research Agents Hack — IIT Madras | Data Extraction Track*

---

## 🎯 Project Summary (200 words)

Researchers conducting systematic reviews spend weeks manually extracting structured findings—experimental benchmarks, clinical trial endpoints, material properties—from PDF papers into spreadsheets. PaperMiner automates this end-to-end with **eight collaborating AI agents**.

The **Parser Agent** extracts layouts, multi-column tables, and captions via PyMuPDF. The **Extractor Agent** reads tables and prose to fill structured schemas, citing exact source locations. The **Validator Agent** cross-checks extractions against raw text, triggering automatic re-extraction upon detecting low confidence.

Crucially, the **Adversarial Red-Team Auditor** actively stress-tests extractions against ablation traps, baseline misattributions, and cherry-picked metrics, issuing an **Auditable Data Integrity Certificate**. The **Vision Agent** extracts data from complex figures and charts using Gemini Multimodal Vision. The **Citation Agent** verifies bibliography citations. The **Schema Builder** auto-detects paper domains or translates natural language into typed Pydantic schemas. In batch mode, the **Synthesis Agent** performs automated cross-paper meta-analysis, generating comparison matrices, consensus takeaways, and interactive Plotly visualizations (forest plots and benchmark charts).

With **1-Click arXiv ingestion** and an **Interactive Visual Grounding Inspector** highlighting source evidence directly on PDF pages, PaperMiner delivers verifiable, audit-ready data in 5 export formats (JSON/CSV/Excel/LaTeX/Markdown). Average cost: ~$0.015/paper.

---

## 🏗️ 8-Agent Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   ORCHESTRATOR AGENT                                   │
│    Plans Strategy · Delegates Tasks · Manages Error Recovery & Low-Confidence Retries   │
│    Coordinates Batch Meta-Analysis · Assembles 5 Export Formats & Audit Trail         │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬────┘
       │          │          │          │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼          ▼          ▼          ▼
┌────────────┐┌────────────┐┌────────────┐┌────────────┐┌────────────┐┌────────────┐┌────────────┐┌────────────┐
│   PARSER   ││  SCHEMA    ││ EXTRACTOR  ││   VISION   ││ VALIDATOR  ││  RED-TEAM  ││  CITATION  ││ SYNTHESIS  │
│   AGENT    ││  BUILDER   ││   AGENT    ││   AGENT    ││   AGENT    ││  AUDITOR   ││   AGENT    ││   AGENT    │
│            ││            ││            ││            ││            ││            ││            ││            │
│ • PyMuPDF  ││ • Domain   ││ • Schema-  ││ • Multimodal││ • Source   ││ • Ablation ││ • Biblio   ││ • Cross-   │
│   layout   ││   detector ││   guided   ││   vision   ││   cross-   ││   trap hunt││   matching ││   paper    │
│ • Tables   ││ • NL →     ││ • Multi-   ││ • Bar/Line ││   check    ││ • Baseline ││ • Citation ││   matrix   │
│ • Figures  ││   Pydantic ││   pass     ││   charts   ││ • Confi-   ││   check    ││   claim    ││ • Consensus│
│ • Sections ││   schemas  ││ • Citations││ • Image tab││   dence    ││ • Integrity││   audit    ││ • Gaps     │
└────────────┘└────────────┘└────────────┘└────────────┘└────────────┘└────────────┘└────────────┘└────────────┘
```

---

## 🌟 Hackathon Highlights & Winning Differentiators

| Feature | How It Works | Judging Impact |
|---|---|---|
| **⚔️ Adversarial Red-Team Auditor** | Actively attacks extractions to hunt for baseline confusions and ablation traps; awards an **Auditable Integrity Certificate**. | **Agent Collaboration (25%) + Originality (10%)** |
| **🎯 Visual Grounding Inspector** | Renders the exact PDF page with **neon bounding boxes** around the cited sentence or table cell. | **Working Demo (20%) + Research Utility (30%)** |
| **🌐 1-Click arXiv Ingestion** | Paste an arXiv ID/URL or search keywords to auto-stream papers into the multi-agent pipeline with zero local downloads. | **Working Demo (20%)** |
| **📈 Automated Meta-Analysis Charts** | Generates interactive Plotly visualizations (Comparative Benchmark Charts, Clinical Forest Plots, Property Distributions). | **Research Utility (30%)** |
| **⚡ Smart Auto-Detect Schema** | Schema Builder inspects any uploaded paper (Medicine, ML, Materials, Chemistry) and tailors the schema automatically. | **Research Utility (30%)** |
| **👁️ Gemini Multimodal Vision AI** | Renders pages to high-res images to extract data embedded inside plots, charts, and scanned tables. | **Originality (10%)** |
| **📥 5 Auditable Export Formats** | Export validated data to **JSON**, **CSV**, **Excel (.xlsx)**, **LaTeX (.tex)**, and **Markdown Audit Logs**. | **Cost Efficiency (15%)** |

---

## 🚀 Quick Start

### 1. Installation
```bash
git clone https://github.com/YOUR_USERNAME/PaperMiner.git
cd PaperMiner
pip install -r requirements.txt
cp .env.example .env
# Add your GEMINI_API_KEY in .env
```

### 2. Launch Interactive Web Suite
```bash
streamlit run app.py
```
Open **http://localhost:8501** in your browser.

### 3. Run CLI Benchmark & Automated Test Suite
```bash
# Run automated test suite (12 passed tests)
python -m pytest tests/ -v

# Run full pipeline CLI demo
python run_demo.py --pdf sample_papers/attention_is_all_you_need.pdf --schema ml_benchmarks
```

---

## 📊 Reproducibility & Benchmark Metrics

### Verified Benchmark on *Attention Is All You Need* (15 pages, 8 tables):
- **Records Extracted**: **29 structured benchmark records**
- **Validator Confidence**: **29/29 verified as HIGH (100%)**
- **Red-Team Robustness Score**: **100/100 (PASSED_ROBUST)**
- **Total API Cost**: **$0.0144** (< 1.5 cents)
- **Pipeline Duration**: **59.1 seconds**
- **Automated Tests**: **12 / 12 passing**

---

## 📋 Judging Rubric Alignment

| Criterion | Weight | How PaperMiner Leads |
|---|---|---|
| **Research Utility** | 30% | Universal across all scientific domains (Medical, ML, Materials); replaces weeks of meta-analysis with 60 seconds. |
| **Agent Collaboration** | 25% | 8 specialized agents with typed message handoffs, feedback retry loops, and adversarial stress-testing. |
| **Working Demo** | 20% | 1-Click arXiv ingestion + live PDF bounding box grounding inspector + interactive Plotly charts. |
| **Cost Efficiency** | 15% | Transparent per-agent token and cost ledger (~$0.015/paper on Gemini Flash). |
| **Originality** | 10% | Adversarial integrity certificates + multimodal chart vision + dynamic NL schema generation. |

---

## 📝 License
MIT License — Copyright (c) 2026.
