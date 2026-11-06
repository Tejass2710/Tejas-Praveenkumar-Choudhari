import time
from typing import Dict, Any, List
import pandas as pd

from project_b.detectors_rules import DeclarativeRuleDetectors
from project_b.detectors_statistical import StatisticalDetectors
from project_b.detectors_llm import LLMReviewDetector

class HybridDataQualityPipeline:
    """
    Task 5: The Winning Multi-Tiered Hybrid Data Quality Pipeline.
    Combines cheap declarative rules on every row, statistical checks on the batch,
    and LLM semantic review strictly on flagged or sampled rows.
    """

    def __init__(self, gemini_client=None):
        self.rules = DeclarativeRuleDetectors()
        self.stats = StatisticalDetectors()
        self.llm = LLMReviewDetector(client=gemini_client) if gemini_client else None

    def run_pipeline(self, df: pd.DataFrame, sample_llm_rows: int = 10) -> Dict[str, Any]:
        start_time = time.time()
        pipeline_report = {
            "total_rows": len(df),
            "tier1_rules": {},
            "tier2_statistics": {},
            "tier3_llm": {},
            "issues_summary": [],
            "latency_ms": 0.0,
            "estimated_cost_usd": 0.0
        }

        # -----------------------------------------------------------------
        # TIER 1: Declarative Rules on Every Row (Zero API cost, ~0.1 ms)
        # -----------------------------------------------------------------
        t1_start = time.time()
        r_schema = self.rules.check_schema_columns(df)
        r_types = self.rules.check_column_types(df)
        r_dates = self.rules.check_date_formats(df)
        r_coords = self.rules.check_lat_long_bounds(df)
        r_dups = self.rules.check_exact_duplicates(df)
        r_chrono = self.rules.check_chronology(df)
        r_zip = self.rules.check_zip_borough_consistency(df)
        r_pii = self.rules.check_pii_leakage(df)
        t1_duration = (time.time() - t1_start) * 1000

        pipeline_report["tier1_rules"] = {
            "duration_ms": round(t1_duration, 2),
            "schema_valid": r_schema["passed"],
            "column_types_valid": r_types["passed"],
            "date_formats_valid": r_dates["passed"],
            "coordinates_valid": r_coords["passed"],
            "exact_duplicates": r_dups["corrupted_rows"],
            "chronology_violations": r_chrono["corrupted_rows"],
            "zip_borough_mismatches": r_zip["corrupted_rows"],
            "pii_leaks": r_pii["corrupted_rows"]
        }

        for check_res in [r_schema, r_types, r_dates, r_coords, r_dups, r_chrono, r_zip, r_pii]:
            if not check_res["passed"]:
                pipeline_report["issues_summary"].append(f"[Tier 1 Alert]: {check_res['alert']}")

        # -----------------------------------------------------------------
        # TIER 2: Statistical Batch Checks (Zero API cost, ~10 ms)
        # -----------------------------------------------------------------
        t2_start = time.time()
        s_near_dups = self.stats.detect_near_duplicates(df)
        s_null_spike = self.stats.detect_agency_null_spike(df)
        s_taxonomy = self.stats.detect_category_cooccurrence_anomalies(df)
        t2_duration = (time.time() - t2_start) * 1000

        pipeline_report["tier2_statistics"] = {
            "duration_ms": round(t2_duration, 2),
            "near_duplicates_found": s_near_dups["flagged_pairs"],
            "agency_null_spikes": s_null_spike["spiking_agencies"],
            "cooccurrence_anomalies": s_taxonomy["anomalous_pairs"]
        }

        for check_res in [s_near_dups, s_null_spike, s_taxonomy]:
            if not check_res["passed"]:
                pipeline_report["issues_summary"].append(f"[Tier 2 Alert]: {check_res['alert']}")

        # -----------------------------------------------------------------
        # TIER 3: LLM Semantic Review (Strictly on Flagged or Small Sample)
        # -----------------------------------------------------------------
        t3_start = time.time()
        llm_cost = 0.0
        if self.llm and len(df) > 0:
            # Smart Routing: Audit rows that triggered taxonomy or text suspicion,
            # or inspect a small representative sample to prevent burning API quota.
            llm_res = self.llm.audit_batch(df, max_rows=sample_llm_rows)
            t3_duration = (time.time() - t3_start) * 1000

            # Approximate cost for Gemini Flash (~1,500 input tokens = ~$0.00015)
            llm_cost = 0.00015

            pipeline_report["tier3_llm"] = {
                "duration_ms": round(t3_duration, 2),
                "rows_audited": sample_llm_rows,
                "flagged_rows": llm_res["flagged_rows"],
                "results": llm_res["results"]
            }

            if not llm_res["passed"]:
                pipeline_report["issues_summary"].append(f"[Tier 3 Alert]: {llm_res['alert']}")
        else:
            pipeline_report["tier3_llm"] = {
                "status": "Skipped (No client or empty batch)",
                "duration_ms": 0.0
            }

        total_duration = (time.time() - start_time) * 1000
        pipeline_report["latency_ms"] = round(total_duration, 2)
        pipeline_report["estimated_cost_usd"] = round(llm_cost, 6)

        return pipeline_report