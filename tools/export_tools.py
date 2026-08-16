"""
Export tools for converting validated extractions to JSON, CSV, Excel, LaTeX, and audit reports.
"""

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any


def to_json(
    extractions: list[dict],
    validation_results: list[dict],
    metadata: dict | None = None,
) -> str:
    """Export extractions as pretty-printed JSON with validation info."""
    output = {
        "paperminer_version": "1.0.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
        "total_records": len(extractions),
        "records": [],
    }

    for i, extraction in enumerate(extractions):
        record = {**extraction}
        if i < len(validation_results):
            record["_validation"] = validation_results[i]
        output["records"].append(record)

    return json.dumps(output, indent=2, ensure_ascii=False, default=str)


def to_csv(extractions: list[dict]) -> str:
    """Flatten extractions and export as CSV string."""
    if not extractions:
        return ""

    # Collect all unique keys across all records
    all_keys: list[str] = []
    for record in extractions:
        for key in record:
            if key not in all_keys and not key.startswith("_"):
                all_keys.append(key)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=all_keys, extrasaction="ignore")
    writer.writeheader()

    for record in extractions:
        # Flatten nested values to strings
        flat_record = {}
        for key in all_keys:
            value = record.get(key, "")
            if isinstance(value, (list, dict)):
                flat_record[key] = json.dumps(value, ensure_ascii=False)
            else:
                flat_record[key] = str(value) if value is not None else ""
        writer.writerow(flat_record)

    return output.getvalue()


def to_audit_report(
    filename: str,
    extractions: list[dict],
    validation_results: list[dict],
    interaction_log: list[dict],
    cost_report: str,
) -> str:
    """Generate a full audit trail as a markdown report."""
    lines = [
        f"# PaperMiner Audit Report",
        f"**Source:** {filename}",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "---",
        "",
        "## Extraction Summary",
        f"**Records extracted:** {len(extractions)}",
        "",
    ]

    # Validation summary
    if validation_results:
        high = sum(1 for v in validation_results if v.get("overall_confidence") == "HIGH")
        medium = sum(1 for v in validation_results if v.get("overall_confidence") == "MEDIUM")
        low = sum(1 for v in validation_results if v.get("overall_confidence") == "LOW")
        lines.append("## Validation Summary")
        lines.append(f"- 🟢 HIGH confidence: {high}")
        lines.append(f"- 🟡 MEDIUM confidence: {medium}")
        lines.append(f"- 🔴 LOW confidence: {low}")
        lines.append("")

    # Extracted data
    lines.append("## Extracted Records")
    for i, record in enumerate(extractions, 1):
        lines.append(f"\n### Record {i}")
        for key, value in record.items():
            if not key.startswith("_"):
                lines.append(f"- **{key}:** {value}")
        
        if i <= len(validation_results):
            vr = validation_results[i - 1]
            lines.append(f"\n  *Confidence: {vr.get('overall_confidence', 'N/A')}*")
            issues = vr.get("issues", [])
            if issues:
                lines.append("  *Issues:*")
                for issue in issues:
                    lines.append(f"  - ⚠️ {issue}")
        lines.append("")

    # Agent interaction log
    lines.append("## Agent Interaction Log")
    lines.append(f"**Total interactions:** {len(interaction_log)}")
    lines.append("")
    for entry in interaction_log:
        sender = entry.get("sender", "?")
        receiver = entry.get("receiver", "?")
        msg_type = entry.get("type", "?")
        lines.append(f"- **{sender}** → **{receiver}** [{msg_type}]")
    lines.append("")

    # Cost report
    lines.append("## Cost Report")
    lines.append("```")
    lines.append(cost_report)
    lines.append("```")

    return "\n".join(lines)


def to_excel(extractions: list[dict]) -> bytes:
    """Export extractions as an Excel (.xlsx) file. Returns bytes."""
    import pandas as pd

    if not extractions:
        df = pd.DataFrame()
    else:
        clean = [{k: v for k, v in r.items() if not k.startswith("_")} for r in extractions]
        df = pd.DataFrame(clean)

    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


def to_latex(extractions: list[dict]) -> str:
    """Export extractions as a LaTeX table string."""
    if not extractions:
        return "% No data to export"

    # Collect keys
    keys: list[str] = []
    for record in extractions:
        for k in record:
            if k not in keys and not k.startswith("_"):
                keys.append(k)

    def _escape(s: str) -> str:
        """Escape special LaTeX characters."""
        for ch in ("&", "%", "$", "#", "_", "{", "}"):
            s = s.replace(ch, f"\\{ch}")
        s = s.replace("~", "\\textasciitilde{}")
        s = s.replace("^", "\\textasciicircum{}")
        return s

    lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{PaperMiner Extracted Data}",
        "\\label{tab:paperminer}",
        "\\begin{tabular}{" + "l" * len(keys) + "}",
        "\\toprule",
        " & ".join(f"\\textbf{{{_escape(k)}}}" for k in keys) + " \\\\",
        "\\midrule",
    ]

    for record in extractions:
        cells = []
        for k in keys:
            val = record.get(k, "")
            if isinstance(val, (list, dict)):
                val = json.dumps(val, ensure_ascii=False)
            cells.append(_escape(str(val) if val is not None else ""))
        lines.append(" & ".join(cells) + " \\\\")

    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        "\\end{table}",
    ])

    return "\n".join(lines)

