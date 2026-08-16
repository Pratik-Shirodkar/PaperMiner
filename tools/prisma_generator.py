"""
PRISMA 2020 Flow Diagram Generator.
Generates publication-ready PRISMA (Preferred Reporting Items for Systematic Reviews
and Meta-Analyses) flow diagrams using Plotly.
"""

from typing import Any, Optional
import plotly.graph_objects as go


def generate_prisma_flow_chart(
    total_identified: int,
    screened_count: int,
    excluded_screening: int,
    assessed_eligibility: int,
    excluded_eligibility: int,
    included_count: int,
    domain_name: str = "Systematic Literature Review",
) -> go.Figure:
    """
    Generate an interactive PRISMA 2020 flow diagram for systematic literature reviews.
    """
    fig = go.Figure()

    # Step Boxes Data
    steps = [
        # (x, y, title, subtitle, color, border_color)
        (
            0.5, 0.90,
            "<b>1. IDENTIFICATION</b>",
            f"Records identified from sources (arXiv / Uploads)<br><b>(n = {total_identified})</b>",
            "#1E293B", "#475569"
        ),
        (
            0.5, 0.65,
            "<b>2. SCREENING</b>",
            f"Records screened by Document Parser<br><b>(n = {screened_count})</b>",
            "#1E293B", "#475569"
        ),
        (
            0.85, 0.65,
            "<b>EXCLUDED (SCREENING)</b>",
            f"Malformed tables / missing text<br><b>(n = {excluded_screening})</b>",
            "#2A1A1E", "#DC2626"
        ),
        (
            0.5, 0.40,
            "<b>3. ELIGIBILITY</b>",
            f"Full-text records assessed by Extractor<br><b>(n = {assessed_eligibility})</b>",
            "#1E293B", "#475569"
        ),
        (
            0.85, 0.40,
            "<b>EXCLUDED (AUDIT)</b>",
            f"Failed red-team ablation check<br><b>(n = {excluded_eligibility})</b>",
            "#2A1A1E", "#DC2626"
        ),
        (
            0.5, 0.15,
            "<b>4. INCLUDED</b>",
            f"Studies included in quantitative meta-analysis<br><b>(n = {included_count})</b>",
            "#064E3B", "#10B981"
        ),
    ]

    # Draw Boxes
    for x, y, title, subtitle, bg_color, border in steps:
        fig.add_shape(
            type="rect",
            x0=x - 0.18, y0=y - 0.08,
            x1=x + 0.18, y1=y + 0.08,
            fillcolor=bg_color,
            line=dict(color=border, width=2),
            layer="below",
        )
        fig.add_annotation(
            x=x, y=y,
            text=f"<span style='font-size:12px; color:#F3F4F6;'>{title}</span><br><span style='font-size:10px; color:#9CA3AF;'>{subtitle}</span>",
            showarrow=False,
            font=dict(family="Inter, sans-serif", size=11),
            align="center",
        )

    # Draw Connecting Arrows
    arrows = [
        # (x0, y0, x1, y1)
        (0.5, 0.82, 0.5, 0.73),      # Identification -> Screening
        (0.68, 0.65, 0.77, 0.65),    # Screening -> Excluded
        (0.5, 0.57, 0.5, 0.48),      # Screening -> Eligibility
        (0.68, 0.40, 0.77, 0.40),    # Eligibility -> Excluded
        (0.5, 0.32, 0.5, 0.23),      # Eligibility -> Included
    ]

    for x0, y0, x1, y1 in arrows:
        fig.add_annotation(
            x=x1, y=y1,
            ax=x0, ay=y0,
            xref="x", yref="y",
            axref="x", ayref="y",
            showarrow=True,
            arrowhead=2,
            arrowsize=1.2,
            arrowwidth=2,
            arrowcolor="#6366F1",
        )

    fig.update_layout(
        title=dict(
            text=f"<b>PRISMA 2020 Systematic Review Flow Diagram</b> — <i>{domain_name}</i>",
            font=dict(size=14, color="#E5E7EB"),
            x=0.02,
        ),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0.25, 1.1]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0.05, 1.0]),
        plot_bgcolor="#0A0D14",
        paper_bgcolor="#0A0D14",
        margin=dict(l=20, r=20, t=50, b=20),
        height=480,
    )

    return fig
