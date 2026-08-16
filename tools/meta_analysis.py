"""
Meta-Analysis & Interactive Visualization Tool.
Generates publication-quality Plotly charts from extracted structured datasets.
"""

import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional


def generate_interactive_charts(extractions: list[dict], schema_name: str = "") -> list[dict]:
    """
    Generate interactive Plotly figures based on the extracted data.
    Returns a list of dicts: [{"title": "...", "figure": go.Figure}].
    """
    if not extractions:
        return []

    clean_records = [{k: v for k, v in r.items() if not k.startswith("_")} for r in extractions]
    df = pd.DataFrame(clean_records)

    charts = []

    # Clean numeric helper
    def extract_numeric(val):
        if val is None:
            return None
        match = re.search(r'[-+]?\d*\.?\d+', str(val))
        return float(match.group(0)) if match else None

    # Chart 1: ML Benchmarks (Model vs Score)
    if "model_name" in df.columns and "score" in df.columns:
        df["numeric_score"] = df["score"].apply(extract_numeric)
        df_valid = df.dropna(subset=["numeric_score", "model_name"])

        if len(df_valid) > 0:
            # Color by dataset if available
            color_col = "dataset" if "dataset" in df.columns and df["dataset"].nunique() > 1 else None

            fig = px.bar(
                df_valid.head(25),
                x="model_name",
                y="numeric_score",
                color=color_col,
                title="🏆 Comparative Benchmark Performance",
                labels={"model_name": "Model / Method", "numeric_score": "Score (Extracted)"},
                template="plotly_dark",
            )
            fig.update_layout(
                plot_bgcolor="rgba(20,20,35,0.8)",
                paper_bgcolor="rgba(15,12,41,0.9)",
                font={"family": "Inter", "color": "#e0e0f0"},
                xaxis_tickangle=-45,
            )
            charts.append({"title": "Benchmark Comparison Chart", "figure": fig})

    # Chart 2: Clinical / Drug Trials (Forest Plot / Effect Size Distribution)
    if "drug_name" in df.columns or "primary_endpoint" in df.columns:
        score_col = "result" if "result" in df.columns else ("p_value" if "p_value" in df.columns else None)
        label_col = "drug_name" if "drug_name" in df.columns else "condition"

        if score_col and label_col in df.columns:
            df["numeric_val"] = df[score_col].apply(extract_numeric)
            df_med = df.dropna(subset=["numeric_val", label_col])

            if len(df_med) > 0:
                fig = px.scatter(
                    df_med.head(20),
                    x="numeric_val",
                    y=label_col,
                    size=[12] * len(df_med),
                    color=label_col,
                    title="💊 Clinical Effect Size & Endpoint Forest Plot",
                    labels={"numeric_val": f"Value ({score_col})", label_col: "Intervention / Group"},
                    template="plotly_dark",
                )
                fig.update_layout(
                    plot_bgcolor="rgba(20,20,35,0.8)",
                    paper_bgcolor="rgba(15,12,41,0.9)",
                    font={"family": "Inter", "color": "#e0e0f0"},
                )
                charts.append({"title": "Clinical Effect Forest Plot", "figure": fig})

    # Chart 3: Generic / Material Properties Distribution
    if not charts and len(df.columns) >= 2:
        # Find any numeric-convertible column
        for col in df.columns:
            if col in ("source_location", "confidence", "notes"):
                continue
            numeric_series = df[col].apply(extract_numeric)
            if numeric_series.notna().sum() >= 2:
                label_col = df.columns[0] if df.columns[0] != col else df.columns[1]
                df["num_col"] = numeric_series
                df_gen = df.dropna(subset=["num_col", label_col])
                
                fig = px.bar(
                    df_gen.head(20),
                    x=label_col,
                    y="num_col",
                    title=f"📊 Extracted Distribution: {col}",
                    labels={label_col: "Entity", "num_col": col},
                    template="plotly_dark",
                )
                fig.update_layout(
                    plot_bgcolor="rgba(20,20,35,0.8)",
                    paper_bgcolor="rgba(15,12,41,0.9)",
                    font={"family": "Inter", "color": "#e0e0f0"},
                )
                charts.append({"title": f"{col} Distribution", "figure": fig})
                break

    return charts
