import os
import re
import pandas as pd
from typing import Dict, Any, List

class NYC311Profiler:
    """
    Task 1: Real 2023 NYC 311 Dataset Profiler.
    Scans the raw, untouched public dataset to discover naturally occurring
    data quality defects, returning exact counts and real-world examples.
    """

    PHONE_REGEX = re.compile(r'(\b\d{3}[-.\s]??\d{3}[-.\s]??\d{4}\b|\(\d{3}\)\s*\d{3}[-.\s]??\d{4})')
    EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Dataset not found at: {csv_path}")
        self.df = pd.read_csv(csv_path, low_memory=False)

    def profile_all(self) -> Dict[str, Any]:
        report = {
            "total_rows_analyzed": len(self.df),
            "findings": {}
        }

        # 1. Null / Missing Descriptors
        if "descriptor" in self.df.columns:
            null_desc_count = int(self.df["descriptor"].isna().sum())
            null_desc_pct = round((null_desc_count / len(self.df)) * 100, 2)
            report["findings"]["missing_descriptors"] = {
                "count": null_desc_count,
                "percentage": null_desc_pct,
                "example_agencies": self.df[self.df["descriptor"].isna()]["agency"].value_counts().head(3).to_dict() if null_desc_count > 0 else {}
            }

        # 2. Missing Spatial Coordinates
        if "latitude" in self.df.columns and "longitude" in self.df.columns:
            missing_coords = self.df["latitude"].isna() | self.df["longitude"].isna()
            missing_coords_count = int(missing_coords.sum())
            missing_coords_pct = round((missing_coords_count / len(self.df)) * 100, 2)
            report["findings"]["missing_coordinates"] = {
                "count": missing_coords_count,
                "percentage": missing_coords_pct
            }

        # 3. Missing Postal Codes
        if "incident_zip" in self.df.columns:
            missing_zip_count = int(self.df["incident_zip"].isna().sum())
            missing_zip_pct = round((missing_zip_count / len(self.df)) * 100, 2)
            report["findings"]["missing_incident_zip"] = {
                "count": missing_zip_count,
                "percentage": missing_zip_pct
            }

        # 4. Actual Chronology Violations (Closed < Created)
        if "created_date" in self.df.columns and "closed_date" in self.df.columns:
            valid_dates = self.df["created_date"].notna() & self.df["closed_date"].notna()
            sub = self.df[valid_dates].copy()
            created = pd.to_datetime(sub["created_date"], errors="coerce")
            closed = pd.to_datetime(sub["closed_date"], errors="coerce")
            chrono_violations = (closed < created) & created.notna() & closed.notna()
            chrono_count = int(chrono_violations.sum())
            
            examples = []
            if chrono_count > 0:
                for idx in sub[chrono_violations].head(3).index:
                    examples.append({
                        "row_id": int(idx),
                        "created": str(sub.loc[idx, "created_date"]),
                        "closed": str(sub.loc[idx, "closed_date"])
                    })

            report["findings"]["chronology_inconsistencies"] = {
                "count": chrono_count,
                "examples": examples
            }

        # 5. Potential PII Leaks in Public Text
        if "resolution_description" in self.df.columns:
            text_series = self.df["resolution_description"].dropna().astype(str)
            phone_matches = text_series.apply(lambda t: bool(self.PHONE_REGEX.search(t)))
            email_matches = text_series.apply(lambda t: bool(self.EMAIL_REGEX.search(t)))
            pii_matches = phone_matches | email_matches
            pii_count = int(pii_matches.sum())
            
            examples_pii = []
            if pii_count > 0:
                for idx in text_series[pii_matches].head(2).index:
                    examples_pii.append({
                        "row_id": int(idx),
                        "snippet": text_series.loc[idx][:120] + "..."
                    })

            report["findings"]["pii_in_text"] = {
                "count": pii_count,
                "examples": examples_pii
            }

        return report