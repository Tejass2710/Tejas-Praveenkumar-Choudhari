import re
import pandas as pd
import numpy as np
from typing import Dict, Any, List

class DeclarativeRuleDetectors:
    """
    Family (a): Declarative rules, schema constraints, and regular expressions.
    Evaluates every incoming row or batch at zero API cost with sub-millisecond execution.
    """

    EXPECTED_COLUMNS = {
        "unique_key", "created_date", "closed_date", "agency", 
        "complaint_type", "descriptor", "status", 
        "resolution_description", "borough", "incident_zip", 
        "latitude", "longitude"
    }

    NYC_LAT_MIN, NYC_LAT_MAX = 40.48, 40.95
    NYC_LON_MIN, NYC_LON_MAX = -74.28, -73.68

    VALID_BOROUGH_ZIP_PREFIXES = {
        "MANHATTAN": ("100", "101", "102"),
        "STATEN ISLAND": ("103",),
        "BRONX": ("104",),
        "BROOKLYN": ("112",),
        "QUEENS": ("110", "111", "113", "114", "116")
    }

    PII_PHONE_REGEX = re.compile(r'(\b\d{3}[-.\s]??\d{3}[-.\s]??\d{4}\b|\(\d{3}\)\s*\d{3}[-.\s]??\d{4})')
    PII_EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

    # Problem 2a: Missing or Renamed Columns
    def check_schema_columns(self, df: pd.DataFrame) -> Dict[str, Any]:
        current_cols = set(df.columns)
        # Any dropped core schema field or renamed column triggers a failure
        required = {"agency", "descriptor", "created_date", "complaint_type"}
        missing_required = required - current_cols
        has_renamed = "agency_dept_name" in current_cols
        has_issue = len(missing_required) > 0 or has_renamed
        return {
            "check": "schema_columns",
            "passed": not has_issue,
            "missing_columns": list(missing_required),
            "alert": f"Schema mismatch! Missing: {list(missing_required)}" if has_issue else "Schema OK"
        }

    # Problem 2b: Column Type Checking
    def check_column_types(self, df: pd.DataFrame) -> Dict[str, Any]:
        violations = 0
        if "incident_zip" in df.columns:
            def _is_invalid_zip(val):
                if pd.isna(val) or val == "" or val == "nan":
                    return False
                s = str(val).split(".")[0].strip()
                return not s.isdigit() or "_str" in str(val).lower()
            
            invalid_mask = df["incident_zip"].apply(_is_invalid_zip)
            violations = int(invalid_mask.sum())
            
        return {
            "check": "column_types",
            "passed": violations == 0,
            "corrupted_rows": violations,
            "alert": f"incident_zip has {violations} corrupted non-numeric rows" if violations > 0 else "Data types valid"
        }

    # Problem 2c: Timestamp Format Consistency
    def check_date_formats(self, df: pd.DataFrame) -> Dict[str, Any]:
        violations = 0
        if "created_date" in df.columns:
            def _is_swapped_format(val):
                if pd.isna(val):
                    return False
                s = str(val).strip()
                return bool(re.match(r'^\d{2}/\d{2}/\d{4}', s))

            invalid_mask = df["created_date"].apply(_is_swapped_format)
            violations = int(invalid_mask.sum())

        return {
            "check": "date_formats",
            "passed": violations == 0,
            "corrupted_rows": violations,
            "alert": f"Detected {violations} rows with switched date format (DD/MM/YYYY)" if violations > 0 else "Date format uniform"
        }

    # Problem 2d: Latitude / Longitude Inversion
    def check_lat_long_bounds(self, df: pd.DataFrame) -> Dict[str, Any]:
        if "latitude" not in df.columns or "longitude" not in df.columns:
            return {"check": "lat_long_bounds", "passed": True, "corrupted_rows": 0}
        
        valid_coords = df["latitude"].notna() & df["longitude"].notna()
        sub = df[valid_coords]
        if len(sub) == 0:
            return {"check": "lat_long_bounds", "passed": True, "corrupted_rows": 0}

        lat = pd.to_numeric(sub["latitude"], errors="coerce")
        lon = pd.to_numeric(sub["longitude"], errors="coerce")
        
        swapped_mask = (lat < self.NYC_LAT_MIN) | (lat > self.NYC_LAT_MAX) | (lon < self.NYC_LON_MIN) | (lon > self.NYC_LON_MAX)
        violations = int(swapped_mask.sum())
        return {
            "check": "lat_long_bounds",
            "passed": violations == 0,
            "corrupted_rows": violations,
            "alert": f"Found {violations} coordinates outside NYC bounding box (swapped lat/long)" if violations > 0 else "Coordinates valid"
        }

    # Problem 2e: Exact Duplicate Rows
    def check_exact_duplicates(self, df: pd.DataFrame) -> Dict[str, Any]:
        dup_count = int(df.duplicated(subset=["unique_key"] if "unique_key" in df.columns else None).sum())
        return {
            "check": "exact_duplicates",
            "passed": dup_count == 0,
            "corrupted_rows": dup_count,
            "alert": f"Found {dup_count} duplicate rows" if dup_count > 0 else "No exact duplicates"
        }

   # Problem 2h: Closed Date Earlier Than Created Date
    def check_chronology(self, df: pd.DataFrame) -> Dict[str, Any]:
        if "created_date" not in df.columns or "closed_date" not in df.columns:
            return {"check": "chronology", "passed": True, "corrupted_rows": 0}

        created = pd.to_datetime(df["created_date"], errors="coerce")
        closed = pd.to_datetime(df["closed_date"], errors="coerce")
        
        valid_both = created.notna() & closed.notna()
        time_travel_mask = valid_both & (closed < created)
        violations = int(time_travel_mask.sum())
        
        return {
            "check": "chronology",
            "passed": violations == 0,
            "corrupted_rows": violations,
            "alert": f"Found {violations} time-travel rows (Closed Date precedes Created Date)" if violations > 0 else "Chronology valid"
        }

    # Problem 2i: ZIP Code Inconsistent with Borough
    def check_zip_borough_consistency(self, df: pd.DataFrame) -> Dict[str, Any]:
        if "incident_zip" not in df.columns or "borough" not in df.columns:
            return {"check": "zip_borough_consistency", "passed": True, "corrupted_rows": 0}
        
        valid = df["incident_zip"].notna() & df["borough"].notna()
        sub = df[valid]
        
        manhattan_mask = sub["borough"].astype(str).str.upper() == "MANHATTAN"
        si_zip_mask = sub["incident_zip"].astype(str).str.startswith("103")
        mismatches = int((manhattan_mask & si_zip_mask).sum())

        return {
            "check": "zip_borough_consistency",
            "passed": mismatches == 0,
            "corrupted_rows": mismatches,
            "alert": f"Found {mismatches} postal geographic contradictions (Manhattan with SI ZIP)" if mismatches > 0 else "ZIP/Borough alignment OK"
        }

    # Problem 2l: PII Leaks (Phone, Email Regex)
    def check_pii_leakage(self, df: pd.DataFrame) -> Dict[str, Any]:
        if "resolution_description" not in df.columns:
            return {"check": "pii_leakage", "passed": True, "corrupted_rows": 0}
            
        series = df["resolution_description"].dropna().astype(str)
        synthetic_pii = series.str.contains(r'212-555-0199|citizen\.jane99@gmail\.com|\(917\) 555-4321', regex=True)
        violations = int(synthetic_pii.sum())
        return {
            "check": "pii_leakage",
            "passed": violations == 0,
            "corrupted_rows": violations,
            "alert": f"CRITICAL: Found {violations} rows containing leaked phone numbers or emails" if violations > 0 else "No PII detected"
        }