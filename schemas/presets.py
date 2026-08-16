"""
Pre-built extraction schemas for common research data types.
These provide ready-to-use extraction templates for the most common use cases.
"""

from schemas.base import ExtractionSchema, SchemaField


ML_BENCHMARK_SCHEMA = ExtractionSchema(
    name="ML Benchmark Results",
    description="Machine learning model performance results including model names, datasets, metrics, and scores. "
                "Common in ML papers that compare multiple models or report experimental results.",
    fields=[
        SchemaField(
            name="model_name",
            field_type="string",
            description="Name of the ML model or method",
            required=True,
            examples=["GPT-4", "BERT-large", "ResNet-50", "Our Method"],
        ),
        SchemaField(
            name="dataset",
            field_type="string",
            description="Name of the benchmark dataset used",
            required=True,
            examples=["ImageNet", "GLUE", "SQuAD", "MMLU"],
        ),
        SchemaField(
            name="metric",
            field_type="string",
            description="Evaluation metric name",
            required=True,
            examples=["Accuracy", "F1", "BLEU", "Perplexity", "mAP"],
        ),
        SchemaField(
            name="score",
            field_type="string",
            description="The metric score/value (keep as string to preserve formatting like '95.2%' or '±0.3')",
            required=True,
            examples=["95.2", "0.891", "42.3%"],
        ),
        SchemaField(
            name="parameters",
            field_type="string",
            description="Model size or parameter count if mentioned",
            required=False,
            examples=["175B", "340M", "7B parameters"],
        ),
        SchemaField(
            name="training_details",
            field_type="string",
            description="Key training details if mentioned (epochs, learning rate, hardware)",
            required=False,
            examples=["100 epochs, lr=1e-4", "8x A100 GPUs"],
        ),
        SchemaField(
            name="source_location",
            field_type="string",
            description="Where in the paper this result was found (table name, section, page)",
            required=True,
            examples=["Table 2", "Section 4.1, page 7", "Figure 3"],
        ),
    ],
    expects_multiple=True,
)


DRUG_TRIAL_SCHEMA = ExtractionSchema(
    name="Clinical / Drug Trial Results",
    description="Results from clinical trials or drug studies, including drug names, sample sizes, "
                "endpoints, and statistical results.",
    fields=[
        SchemaField(
            name="drug_name",
            field_type="string",
            description="Name of the drug, compound, or intervention",
            required=True,
            examples=["Aspirin", "Pembrolizumab", "Compound X-42"],
        ),
        SchemaField(
            name="condition",
            field_type="string",
            description="Disease or condition being treated",
            required=True,
            examples=["Type 2 Diabetes", "Non-small cell lung cancer"],
        ),
        SchemaField(
            name="sample_size",
            field_type="string",
            description="Number of participants/subjects (n=)",
            required=True,
            examples=["n=120", "342 patients", "45 subjects"],
        ),
        SchemaField(
            name="study_design",
            field_type="string",
            description="Type of study (RCT, cohort, case-control, etc.)",
            required=False,
            examples=["Double-blind RCT", "Phase III trial", "Retrospective cohort"],
        ),
        SchemaField(
            name="primary_endpoint",
            field_type="string",
            description="Primary outcome measure",
            required=True,
            examples=["Overall survival", "HbA1c reduction", "Tumor response rate"],
        ),
        SchemaField(
            name="result",
            field_type="string",
            description="Primary result or effect size",
            required=True,
            examples=["HR=0.68", "Mean reduction of 1.2%", "ORR 45.3%"],
        ),
        SchemaField(
            name="p_value",
            field_type="string",
            description="Statistical significance (p-value or confidence interval)",
            required=False,
            examples=["p<0.001", "p=0.034", "95% CI: 0.52-0.89"],
        ),
        SchemaField(
            name="adverse_events",
            field_type="string",
            description="Key adverse events or safety data if reported",
            required=False,
            examples=["Nausea (12%), fatigue (8%)", "Grade 3+ AEs in 15%"],
        ),
        SchemaField(
            name="source_location",
            field_type="string",
            description="Where in the paper this was found",
            required=True,
            examples=["Table 3", "Results section", "Abstract"],
        ),
    ],
    expects_multiple=True,
)


MATERIAL_PROPERTIES_SCHEMA = ExtractionSchema(
    name="Material Properties",
    description="Physical, chemical, or mechanical properties of materials. "
                "Common in materials science, chemistry, and engineering papers.",
    fields=[
        SchemaField(
            name="material_name",
            field_type="string",
            description="Name or composition of the material",
            required=True,
            examples=["Graphene oxide", "Ti-6Al-4V", "PDMS composite"],
        ),
        SchemaField(
            name="property",
            field_type="string",
            description="Name of the measured property",
            required=True,
            examples=["Tensile strength", "Conductivity", "Bandgap energy"],
        ),
        SchemaField(
            name="value",
            field_type="string",
            description="Measured value",
            required=True,
            examples=["45.3", "1.2 × 10⁴", "3.2-3.8"],
        ),
        SchemaField(
            name="unit",
            field_type="string",
            description="Unit of measurement",
            required=True,
            examples=["MPa", "S/cm", "eV", "nm"],
        ),
        SchemaField(
            name="conditions",
            field_type="string",
            description="Measurement conditions (temperature, pressure, etc.)",
            required=False,
            examples=["Room temperature", "300K, vacuum", "pH 7.4"],
        ),
        SchemaField(
            name="method",
            field_type="string",
            description="Measurement method or instrument",
            required=False,
            examples=["XRD", "SEM", "Instron tensile test", "DFT calculation"],
        ),
        SchemaField(
            name="source_location",
            field_type="string",
            description="Where in the paper this was found",
            required=True,
            examples=["Table 1", "Section 3.2", "Figure 4"],
        ),
    ],
    expects_multiple=True,
)


GENERAL_FINDINGS_SCHEMA = ExtractionSchema(
    name="General Research Findings",
    description="General-purpose schema for extracting key findings, claims, and evidence "
                "from any research paper. Use when no specialized schema fits.",
    fields=[
        SchemaField(
            name="finding",
            field_type="string",
            description="A key finding, claim, or result stated in the paper",
            required=True,
            examples=["X increases Y by 30%", "Method A outperforms Method B"],
        ),
        SchemaField(
            name="evidence",
            field_type="string",
            description="Supporting evidence or data for this finding",
            required=True,
            examples=["p<0.05, n=200", "Accuracy improved from 85% to 92%"],
        ),
        SchemaField(
            name="evidence_type",
            field_type="string",
            description="Type of evidence (statistical, experimental, observational, computational)",
            required=False,
            examples=["Statistical test", "Experimental measurement", "Simulation"],
        ),
        SchemaField(
            name="confidence_note",
            field_type="string",
            description="Any caveats, limitations, or qualifications the authors mention",
            required=False,
            examples=["Limited sample size", "Only tested on English", "Preliminary results"],
        ),
        SchemaField(
            name="source_location",
            field_type="string",
            description="Where in the paper this finding appears",
            required=True,
            examples=["Abstract", "Section 5, Discussion", "Table 4"],
        ),
    ],
    expects_multiple=True,
)


# Registry of all preset schemas
PRESET_SCHEMAS: dict[str, ExtractionSchema] = {
    "ml_benchmarks": ML_BENCHMARK_SCHEMA,
    "drug_trials": DRUG_TRIAL_SCHEMA,
    "material_properties": MATERIAL_PROPERTIES_SCHEMA,
    "general_findings": GENERAL_FINDINGS_SCHEMA,
}


def get_schema(name: str) -> ExtractionSchema:
    """Get a preset schema by name."""
    if name not in PRESET_SCHEMAS:
        available = ", ".join(PRESET_SCHEMAS.keys())
        raise ValueError(f"Unknown schema '{name}'. Available: {available}")
    return PRESET_SCHEMAS[name]


def list_schemas() -> list[dict]:
    """List all available schemas with their descriptions."""
    return [
        {
            "key": key,
            "name": schema.name,
            "description": schema.description,
            "field_count": len(schema.fields),
        }
        for key, schema in PRESET_SCHEMAS.items()
    ]
