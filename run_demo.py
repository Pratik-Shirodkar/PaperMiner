"""
PaperMiner CLI Demo Runner
Usage: python run_demo.py --pdf path/to/paper.pdf --schema ml_benchmarks
"""

import argparse
import os
import sys
import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="PaperMiner — Multi-Agent Structured Data Extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_demo.py --pdf paper.pdf --schema ml_benchmarks
  python run_demo.py --pdf paper.pdf --schema drug_trials --output results/
  python run_demo.py --pdf paper.pdf --schema general_findings
        """,
    )
    parser.add_argument("--pdf", required=True, help="Path to the PDF file")
    parser.add_argument(
        "--schema",
        default="general_findings",
        choices=["ml_benchmarks", "drug_trials", "material_properties", "general_findings"],
        help="Extraction schema to use (default: general_findings)",
    )
    parser.add_argument("--output", default="output", help="Output directory (default: output/)")
    args = parser.parse_args()

    # Validate
    if not os.environ.get("GOOGLE_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
        print("❌ Error: Set GEMINI_API_KEY in your .env file or environment")
        print("   Get a free key: https://aistudio.google.com/apikey")
        sys.exit(1)
    
    # Set GOOGLE_API_KEY from GEMINI_API_KEY if needed
    if not os.environ.get("GOOGLE_API_KEY") and os.environ.get("GEMINI_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"❌ Error: PDF file not found: {pdf_path}")
        sys.exit(1)

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  ⛏️  PaperMiner — Multi-Agent Data Extraction")
    print("=" * 60)
    print(f"  PDF:    {pdf_path.name}")
    print(f"  Schema: {args.schema}")
    print(f"  Output: {output_dir}/")
    print("=" * 60)
    print()

    # Import and run
    from agents.orchestrator import OrchestratorAgent

    def progress_callback(stage: str, message: str):
        icons = {
            "planning": "🎯",
            "parsing": "📄",
            "extracting": "🔍",
            "validating": "✅",
            "retrying": "🔄",
            "assembling": "📦",
            "complete": "🏁",
        }
        icon = icons.get(stage, "▶️")
        print(f"  {icon} [{stage.upper():12s}] {message}")

    orchestrator = OrchestratorAgent()
    results = orchestrator.run(
        pdf_path=str(pdf_path),
        schema_name=args.schema,
        progress_callback=progress_callback,
    )

    print()

    if results["status"] == "error":
        print(f"❌ Pipeline failed: {results.get('error')}")
        sys.exit(1)

    # Save outputs
    stem = pdf_path.stem

    # JSON
    json_path = output_dir / f"{stem}_extracted.json"
    json_path.write_text(results["json_export"], encoding="utf-8")
    print(f"  📄 JSON saved:  {json_path}")

    # CSV
    csv_path = output_dir / f"{stem}_extracted.csv"
    csv_path.write_text(results["csv_export"], encoding="utf-8")
    print(f"  📊 CSV saved:   {csv_path}")

    # Audit report
    audit_path = output_dir / f"{stem}_audit.md"
    audit_path.write_text(results["audit_report"], encoding="utf-8")
    print(f"  📝 Audit saved: {audit_path}")

    # Cost report
    print()
    print(results["cost_report"])

    # Summary
    print()
    print(f"  ✅ Extracted {len(results['extractions'])} records")
    print(f"  💰 Total cost: ${results['total_cost_usd']:.6f}")
    print(f"  ⏱️  Duration: {results['pipeline_duration_seconds']:.1f}s")
    print()


if __name__ == "__main__":
    main()
