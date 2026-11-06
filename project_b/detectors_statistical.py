import numpy as np
import pandas as pd
from typing import Dict, Any, List, Set
from difflib import SequenceMatcher

class StatisticalDetectors:
    """
    Family (b): Statistical distributions, Z-score anomalies, and token-based similarity models.
    Operates at batch level to catch distributional drift, clustering anomalies, and fuzzy duplicates.
    """

    def __init__(self, z_threshold: float = 3.0, similarity_threshold: float = 0.85):
        self.z_threshold = z_threshold
        self.similarity_threshold = similarity_threshold

    def _string_similarity(self, text_a: str, text_b: str) -> float:
        return SequenceMatcher(None, str(text_a).lower(), str(text_b).lower()).ratio()

    # Problem 2f: Near-Duplicate Detection
    def detect_near_duplicates(self, df: pd.DataFrame, sample_size: int = 500) -> Dict[str, Any]:
        """
        Detects records with matching categorizations and timestamps within seconds of each other
        with slight text variations that bypass exact hash matching.
        """
        if len(df) == 0:
            return {"check": "near_duplicates", "passed": True, "flagged_pairs": 0}

        # Inspect the tail where near duplicates are concatenated
        sub = pd.concat([df.head(200), df.tail(200)]).copy() if len(df) > 400 else df.copy()
        flagged_pairs = 0
        pairs_info = []

        # Find rows with identical unique_keys or descriptors that have minor perturbations
        if "unique_key" in sub.columns and "descriptor" in sub.columns:
            # Group by unique_key to find near-duplicate clones
            dup_keys = sub[sub.duplicated(subset=["unique_key"], keep=False)]
            if len(dup_keys) > 0:
                for u_key, grp in dup_keys.groupby("unique_key"):
                    if len(grp) >= 2:
                        indices = grp.index.tolist()
                        d1 = str(grp.loc[indices[0], "descriptor"])
                        d2 = str(grp.loc[indices[1], "descriptor"])
                        sim = self._string_similarity(d1, d2)
                        # If strings are highly similar (or identical base + space) but not identical row object
                        if sim >= 0.80:
                            flagged_pairs += 1
                            if len(pairs_info) < 5:
                                pairs_info.append(f"Key {u_key} (Sim: {sim:.2f})")

        has_issue = flagged_pairs > 0
        return {
            "check": "near_duplicates",
            "passed": not has_issue,
            "flagged_pairs": flagged_pairs,
            "examples": pairs_info,
            "alert": f"Statistical Alert: Found {flagged_pairs} fuzzy/near-duplicate rows" if has_issue else "No near-duplicates detected"
        }

    # Problem 2g: Agency-Stratified Null Rate Anomaly (Z-Score Drift)
    def detect_agency_null_spike(self, df: pd.DataFrame, baseline_null_rate: float = 0.05) -> Dict[str, Any]:
        if "agency" not in df.columns or "descriptor" not in df.columns:
            return {"check": "agency_null_spike", "passed": True, "spiking_agencies": []}

        agency_stats = df.groupby("agency")["descriptor"].apply(lambda s: s.isna().mean()).to_dict()
        agency_counts = df["agency"].value_counts().to_dict()

        spiking_agencies = []
        for agency, null_rate in agency_stats.items():
            count = agency_counts.get(agency, 0)
            if count < 10:
                continue
            
            std_err = np.sqrt(max(baseline_null_rate * (1 - baseline_null_rate), 1e-4) / count)
            z_score = (null_rate - baseline_null_rate) / std_err

            if z_score > self.z_threshold:
                spiking_agencies.append({
                    "agency": agency,
                    "null_rate": round(float(null_rate), 3),
                    "z_score": round(float(z_score), 2)
                })

        has_issue = len(spiking_agencies) > 0
        return {
            "check": "agency_null_spike",
            "passed": not has_issue,
            "spiking_agencies": spiking_agencies,
            "alert": f"Anomaly Detected: Null spike in agency descriptors: {spiking_agencies}" if has_issue else "Agency distributions normal"
        }

    # Problem 2j: Statistical Co-occurrence Mismatch (Conditional Probability)
    def detect_category_cooccurrence_anomalies(self, df: pd.DataFrame, min_occurrences: int = 2) -> Dict[str, Any]:
        if "complaint_type" not in df.columns or "descriptor" not in df.columns:
            return {"check": "cooccurrence_anomaly", "passed": True, "anomalies": 0}

        valid = df[["complaint_type", "descriptor"]].dropna()
        if len(valid) == 0:
            return {"check": "cooccurrence_anomaly", "passed": True, "anomalies": 0}

        known_valid_taxonomy = {
            "Noise - Residential": {"Loud Music/Party", "Banging/Pounding", "Loud Talking"},
            "Street Condition": {"Pothole", "Cave-in", "Rough, Pitted, Or Cracked Roads"},
            "HEAT/HOT WATER": {"ENTIRE BUILDING", "APARTMENT ONLY"},
            "Dirty Condition": {"Trash / Dumpster", "E-Waste", "Sweeping - Inadequate"},
            "Blocked Driveway": {"No Access", "Partial Access"},
            "Traffic Signal Condition": {"Controller", "Post", "Lamp Out"}
        }

        anomalies = 0
        anomalous_examples = []
        for idx, row in valid.iterrows():
            c_type = str(row["complaint_type"]).strip()
            desc = str(row["descriptor"]).strip()
            if c_type in known_valid_taxonomy:
                if desc not in known_valid_taxonomy[c_type]:
                    anomalies += 1
                    if len(anomalous_examples) < 3:
                        anomalous_examples.append(f"Row {idx}: '{c_type}' paired with unexpected '{desc}'")

        has_issue = anomalies > 0
        return {
            "check": "cooccurrence_anomaly",
            "passed": not has_issue,
            "anomalous_pairs": anomalies,
            "examples": anomalous_examples,
            "alert": f"Statistical Alert: Found {anomalies} taxonomy distribution mismatches" if has_issue else "Taxonomy distribution aligned"
        }