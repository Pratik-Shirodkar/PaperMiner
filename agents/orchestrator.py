"""
Orchestrator Agent — Coordinates the entire extraction pipeline.
Plans the extraction strategy, dispatches tasks to specialist agents,
handles retries on low-confidence results, and assembles the final output.

Supports: single PDF, multi-PDF batch mode, custom schemas, vision extraction,
citation verification, and cross-paper synthesis.
"""

import json
import time
from typing import Any, Optional

from agents.base import BaseAgent, AgentMessage
from agents.parser import ParserAgent
from agents.extractor import ExtractorAgent
from agents.validator import ValidatorAgent
from agents.vision import VisionAgent
from agents.citation import CitationAgent
from agents.schema_builder import SchemaBuilderAgent
from agents.synthesis import SynthesisAgent
from agents.red_team import RedTeamAgent
from schemas.base import ExtractionSchema
from schemas.presets import PRESET_SCHEMAS, get_schema
from tools.pdf_tools import ParsedDocument
from tools.export_tools import to_json, to_csv, to_audit_report
from utils.cost_tracker import CostTracker


class OrchestratorAgent(BaseAgent):
    """
    The central coordinator for the PaperMiner pipeline.

    Responsibilities:
    - Receives user requests (PDF + schema)
    - Plans extraction strategy
    - Dispatches tasks to Parser → Extractor → Validator (+ Vision, Citation, Red-Team)
    - Handles retry logic when Validator flags issues
    - Assembles and exports final results
    - Batch mode: process multiple PDFs and synthesize results
    """

    MAX_RETRIES = 2

    def __init__(self, cost_tracker: Optional[CostTracker] = None):
        self._cost_tracker = cost_tracker or CostTracker()
        super().__init__(
            name="Orchestrator",
            role="Pipeline coordinator. You manage the multi-agent extraction workflow, "
                 "delegate tasks to specialist agents, and ensure quality through validation.",
            cost_tracker=self._cost_tracker,
        )
        # Core agents
        self.parser = ParserAgent(cost_tracker=self._cost_tracker)
        self.extractor = ExtractorAgent(cost_tracker=self._cost_tracker)
        self.validator = ValidatorAgent(cost_tracker=self._cost_tracker)
        # Extended agents
        self.vision = VisionAgent(cost_tracker=self._cost_tracker)
        self.citation = CitationAgent(cost_tracker=self._cost_tracker)
        self.schema_builder = SchemaBuilderAgent(cost_tracker=self._cost_tracker)
        self.synthesis = SynthesisAgent(cost_tracker=self._cost_tracker)
        self.red_team = RedTeamAgent(cost_tracker=self._cost_tracker)

    # ──────────────────────────────────────────────
    # SINGLE-PDF PIPELINE
    # ──────────────────────────────────────────────

    def run(
        self,
        pdf_path: str,
        schema_name: str = "general_findings",
        custom_schema: Optional[ExtractionSchema] = None,
        enable_vision: bool = False,
        enable_citations: bool = False,
        enable_red_team: bool = False,
        progress_callback: Any = None,
    ) -> dict:
        """Run the complete extraction pipeline on a single PDF."""
        start_time = time.time()

        def _progress(stage: str, message: str):
            if progress_callback:
                progress_callback(stage, message)

        # ─── STEP 0: PLAN & PARSE ───
        _progress("parsing", "Parser Agent: Converting PDF to structured text...")

        self.send_message(
            receiver="Parser Agent",
            message_type="request",
            content={"action": "parse", "pdf_path": pdf_path},
        )

        try:
            parsed_doc = self.parser.parse(pdf_path)
        except Exception as e:
            return self._error_result(f"Parser Agent failed: {str(e)}")

        _progress(
            "parsing",
            f"✓ Parsed {parsed_doc.total_pages} pages, "
            f"{len(parsed_doc.sections)} sections, "
            f"{len(parsed_doc.tables)} tables",
        )

        # Determine Schema
        if custom_schema:
            schema = custom_schema
        elif schema_name == "auto_detect":
            _progress("planning", "Schema Builder: Analyzing paper domain to auto-detect schema...")
            schema = self.schema_builder.detect_and_build_schema_for_doc(
                parsed_doc.full_text, parsed_doc.filename
            )
            _progress("planning", f"✓ Auto-detected schema: '{schema.name}' ({len(schema.fields)} fields)")
        else:
            schema = get_schema(schema_name)

        self.send_message(
            receiver="Pipeline",
            message_type="request",
            content=f"Starting extraction pipeline for {pdf_path} with schema '{schema.name}'",
        )

        # ─── STEP 2: EXTRACT ───
        _progress("extracting", f"Extractor Agent: Extracting {schema.name}...")

        self.send_message(
            receiver="Extractor Agent",
            message_type="request",
            content={"action": "extract", "schema": schema.name},
        )

        try:
            extractions = self.extractor.extract(parsed_doc, schema)
        except Exception as e:
            return self._error_result(f"Extractor Agent failed: {str(e)}")

        if not extractions:
            _progress("extracting", f"⚠ No matching data found for schema '{schema.name}'")
            return self._build_result(
                parsed_doc, schema, [], [], start_time,
                warning=f"No data matching the '{schema.name}' schema was found in this document. "
                        f"Tip: If this is a medical or specialized paper, select 'Clinical / Drug Trial Results', "
                        f"'General Research Findings', or '⚡ Auto-Detect Schema'."
            )

        _progress("extracting", f"✓ Extracted {len(extractions)} records")

        # ─── STEP 2.5: VISION EXTRACTION (optional) ───
        vision_records: list[dict] = []
        if enable_vision:
            _progress("vision", "Vision Agent: Analyzing figures and charts...")
            self.send_message(
                receiver="Vision Agent",
                message_type="request",
                content={"action": "extract_figures", "pdf_path": pdf_path},
            )
            try:
                vision_records = self.vision.extract_from_figures(
                    pdf_path, schema.to_prompt_description()
                )
                if vision_records:
                    extractions.extend(vision_records)
                    _progress("vision", f"✓ Vision found {len(vision_records)} additional records from figures")
                else:
                    _progress("vision", "✓ No additional figure data found")
            except Exception as e:
                _progress("vision", f"⚠ Vision extraction skipped: {e}")

        # ─── STEP 3: VALIDATE ───
        _progress("validating", "Validator Agent: Cross-checking against source...")

        self.send_message(
            receiver="Validator Agent",
            message_type="request",
            content={"action": "validate", "record_count": len(extractions)},
        )

        try:
            validations = self.validator.validate(extractions, parsed_doc)
        except Exception as e:
            _progress("validating", f"⚠ Validation failed: {e}. Returning unvalidated results.")
            return self._build_result(
                parsed_doc, schema, extractions, [], start_time,
                warning=f"Validation could not be completed: {str(e)}"
            )

        _progress(
            "validating",
            f"✓ Validated: {sum(1 for v in validations if v.get('overall_confidence') == 'HIGH')} HIGH, "
            f"{sum(1 for v in validations if v.get('overall_confidence') == 'MEDIUM')} MEDIUM, "
            f"{sum(1 for v in validations if v.get('overall_confidence') == 'LOW')} LOW",
        )

        # ─── STEP 4: RETRY LOW-CONFIDENCE ───
        low_confidence_indices = [
            i for i, v in enumerate(validations)
            if v.get("overall_confidence") == "LOW"
        ]

        if low_confidence_indices and len(low_confidence_indices) <= 3:
            _progress("retrying", f"Orchestrator: Re-extracting {len(low_confidence_indices)} low-confidence records...")

            self.send_message(
                receiver="Extractor Agent",
                message_type="retry",
                content={
                    "action": "re-extract",
                    "indices": low_confidence_indices,
                    "reason": "Validator flagged as LOW confidence",
                },
            )

            extractions, validations = self._retry_low_confidence(
                extractions, validations, low_confidence_indices,
                parsed_doc, schema,
            )

            _progress("retrying", "✓ Re-extraction complete")

        # ─── STEP 4.5: CITATION VERIFICATION (optional) ───
        citation_results: dict = {}
        if enable_citations:
            _progress("citations", "Citation Agent: Verifying references...")
            self.send_message(
                receiver="Citation Agent",
                message_type="request",
                content={"action": "verify_citations"},
            )
            try:
                citation_results = self.citation.verify_citations(extractions, parsed_doc)
                checks = citation_results.get("citation_checks", [])
                summary = citation_results.get("summary", {})
                _progress(
                    "citations",
                    f"✓ Checked {summary.get('total_citations_checked', len(checks))} citations, "
                    f"{summary.get('references_missing', 0)} missing",
                )
            except Exception as e:
                _progress("citations", f"⚠ Citation check skipped: {e}")

        # ─── STEP 4.8: ADVERSARIAL RED-TEAM AUDIT (optional) ───
        red_team_results: dict = {}
        if enable_red_team:
            _progress("red_team", "Red-Team Auditor: Adversarially stress-testing extractions...")
            self.send_message(
                receiver="Red-Team Auditor",
                message_type="request",
                content={"action": "stress_test", "record_count": len(extractions)},
            )
            try:
                red_team_results = self.red_team.stress_test(extractions, parsed_doc)
                score = red_team_results.get("robustness_score", 100)
                verdict = red_team_results.get("stress_test_verdict", "PASSED")
                _progress("red_team", f"✓ Red-team audit complete: {score}/100 robustness ({verdict})")
            except Exception as e:
                _progress("red_team", f"⚠ Red-team audit skipped: {e}")

        # ─── STEP 5: ASSEMBLE RESULTS ───
        _progress("assembling", "Orchestrator: Assembling final results...")

        result = self._build_result(
            parsed_doc, schema, extractions, validations, start_time
        )
        result["vision_records"] = len(vision_records)
        result["citation_results"] = citation_results
        result["red_team_audit"] = red_team_results
        result["pdf_path"] = pdf_path

        total_time = time.time() - start_time
        _progress(
            "complete",
            f"✓ Pipeline complete in {total_time:.1f}s | "
            f"Cost: ${self._cost_tracker.total_cost_usd:.6f} | "
            f"{len(extractions)} records extracted",
        )

        return result

    # ──────────────────────────────────────────────
    # BATCH (MULTI-PDF) PIPELINE
    # ──────────────────────────────────────────────

    def run_batch(
        self,
        pdf_paths: list[str],
        schema_name: str = "general_findings",
        custom_schema: Optional[ExtractionSchema] = None,
        enable_vision: bool = False,
        enable_citations: bool = False,
        progress_callback: Any = None,
    ) -> dict:
        """
        Run extraction on multiple PDFs and synthesize results.
        """
        def _progress(stage: str, message: str):
            if progress_callback:
                progress_callback(stage, message)

        _progress("batch_start", f"Starting batch extraction on {len(pdf_paths)} papers...")

        batch_results: list[dict] = []
        all_extractions: list[dict] = []
        all_validations: list[dict] = []
        schema = custom_schema or (get_schema(schema_name) if schema_name != "auto_detect" else None)

        for i, pdf_path in enumerate(pdf_paths, 1):
            _progress("batch_progress", f"Processing paper {i}/{len(pdf_paths)}: {pdf_path.split('/')[-1].split(chr(92))[-1]}...")

            # Create a fresh orchestrator for each paper to reset agent logs
            sub_orchestrator = OrchestratorAgent(cost_tracker=self._cost_tracker)
            result = sub_orchestrator.run(
                pdf_path=pdf_path,
                schema_name=schema_name,
                custom_schema=custom_schema,
                enable_vision=enable_vision,
                enable_citations=enable_citations,
            )

            batch_results.append(result)

            # Tag extractions with source paper
            for rec in result.get("extractions", []):
                rec["_source_paper"] = result.get("filename", f"paper_{i}")
                all_extractions.append(rec)
            all_validations.extend(result.get("validations", []))

        _progress("batch_progress", f"✓ All {len(pdf_paths)} papers processed")

        # ─── SYNTHESIS ───
        _progress("synthesizing", "Synthesis Agent: Comparing results across papers...")
        synthesis_result = {}
        schema_title = schema.name if schema else "Auto-Detected"
        if len(batch_results) > 1:
            try:
                synthesis_result = self.synthesis.synthesize(batch_results, schema_title)
                takeaways = synthesis_result.get("key_takeaways", [])
                _progress("synthesizing", f"✓ Synthesis complete: {len(takeaways)} key takeaways")
            except Exception as e:
                _progress("synthesizing", f"⚠ Synthesis skipped: {e}")

        # ─── BUILD BATCH RESULT ───
        total_cost = self._cost_tracker.total_cost_usd
        cost_report = self._cost_tracker.format_report()

        _progress("complete", f"✓ Batch complete | {len(all_extractions)} total records | Cost: ${total_cost:.4f}")

        return {
            "status": "success",
            "mode": "batch",
            "papers_processed": len(pdf_paths),
            "total_records": len(all_extractions),
            "extractions": all_extractions,
            "validations": all_validations,
            "batch_results": batch_results,
            "synthesis": synthesis_result,
            "schema_name": schema_title,
            "cost_report": cost_report,
            "total_cost_usd": total_cost,
            "total_input_tokens": self._cost_tracker.total_input_tokens,
            "total_output_tokens": self._cost_tracker.total_output_tokens,
            "json_export": to_json(all_extractions, all_validations, metadata={
                "mode": "batch",
                "papers": len(pdf_paths),
                "schema": schema_title,
            }),
            "csv_export": to_csv(all_extractions),
            "audit_report": "",
        }

    # ──────────────────────────────────────────────
    # CUSTOM SCHEMA BUILDER
    # ──────────────────────────────────────────────

    def build_custom_schema(self, description: str) -> ExtractionSchema:
        """Build a custom schema from a natural language description."""
        return self.schema_builder.build_schema(description)

    # ──────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────

    def _retry_low_confidence(
        self,
        extractions: list[dict],
        validations: list[dict],
        low_indices: list[int],
        parsed_doc: ParsedDocument,
        schema: ExtractionSchema,
    ) -> tuple[list[dict], list[dict]]:
        """Re-extract and re-validate low-confidence records."""
        issues_context = []
        for idx in low_indices:
            if idx < len(validations):
                issues = validations[idx].get("issues", [])
                corrections = validations[idx].get("corrections", [])
                issues_context.append({
                    "record_index": idx,
                    "issues": issues,
                    "corrections": corrections,
                    "original_record": extractions[idx],
                })

        if not issues_context:
            return extractions, validations

        issues_json = json.dumps(issues_context, indent=2, default=str)
        source_text = parsed_doc.to_markdown()
        if len(source_text) > 30000:
            source_text = source_text[:30000]

        prompt = f"""{schema.to_prompt_description()}

The Validator Agent found issues with these previously extracted records.
Please re-extract the data, paying attention to the validator's feedback.

VALIDATOR ISSUES:
{issues_json}

SOURCE DOCUMENT:
{source_text}

Re-extract ONLY the flagged records with corrections applied.
Return a JSON object: {{"records": [...]}} with corrected records.
Each record must include all schema fields."""

        try:
            result = self.extractor.call_llm_json(
                prompt=prompt,
                system_instruction=(
                    "You are re-extracting data that was previously flagged as low confidence. "
                    "Pay close attention to the validator's feedback and correct any errors. "
                    "Only extract data that is explicitly in the source document."
                ),
                task_description="Re-extraction with validator feedback",
            )

            corrected = result.get("records", [])

            for i, idx in enumerate(low_indices):
                if i < len(corrected) and idx < len(extractions):
                    extractions[idx] = corrected[i]

            corrected_records = [extractions[idx] for idx in low_indices if idx < len(extractions)]
            if corrected_records:
                new_validations = self.validator.validate(corrected_records, parsed_doc)
                for i, idx in enumerate(low_indices):
                    if i < len(new_validations) and idx < len(validations):
                        validations[idx] = new_validations[i]

        except Exception:
            pass

        return extractions, validations

    def _build_result(
        self,
        parsed_doc: ParsedDocument,
        schema: ExtractionSchema,
        extractions: list[dict],
        validations: list[dict],
        start_time: float,
        warning: str = "",
    ) -> dict:
        """Assemble the final pipeline result."""
        total_time = time.time() - start_time

        all_logs = (
            self.get_interaction_log()
            + self.parser.get_interaction_log()
            + self.extractor.get_interaction_log()
            + self.validator.get_interaction_log()
            + self.vision.get_interaction_log()
            + self.citation.get_interaction_log()
        )
        all_logs.sort(key=lambda x: x.get("timestamp", 0))

        json_export = to_json(extractions, validations, metadata={
            "filename": parsed_doc.filename,
            "schema": schema.name,
            "pages": parsed_doc.total_pages,
        })
        csv_export = to_csv(extractions)
        cost_report = self._cost_tracker.format_report()
        audit_report = to_audit_report(
            parsed_doc.filename, extractions, validations, all_logs, cost_report,
        )

        return {
            "status": "success" if not warning else "warning",
            "warning": warning,
            "filename": parsed_doc.filename,
            "schema_name": schema.name,
            "total_pages": parsed_doc.total_pages,
            "sections_found": len(parsed_doc.sections),
            "tables_found": len(parsed_doc.tables),
            "extractions": extractions,
            "validations": validations,
            "json_export": json_export,
            "csv_export": csv_export,
            "audit_report": audit_report,
            "cost_report": cost_report,
            "interaction_log": all_logs,
            "pipeline_duration_seconds": total_time,
            "total_cost_usd": self._cost_tracker.total_cost_usd,
            "total_input_tokens": self._cost_tracker.total_input_tokens,
            "total_output_tokens": self._cost_tracker.total_output_tokens,
        }

    def _error_result(self, error_message: str) -> dict:
        """Build an error result."""
        return {
            "status": "error",
            "error": error_message,
            "extractions": [],
            "validations": [],
            "cost_report": self._cost_tracker.format_report(),
        }
