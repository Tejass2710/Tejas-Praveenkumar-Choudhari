import random
import re
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

class CorruptionInjector:
    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)

    def inject_renamed_or_dropped_column(self, df: pd.DataFrame, drop: bool = False) -> pd.DataFrame:
        df = df.copy()
        if drop:
            if "descriptor" in df.columns:
                df = df.drop(columns=["descriptor"])
        else:
            df = df.rename(columns={"agency": "agency_dept_name"})
        return df

    def inject_column_type_change(self, df: pd.DataFrame, rate: float = 0.15) -> pd.DataFrame:
        df = df.copy()
        if "incident_zip" in df.columns:
            # Cast column to object first so pandas can hold mixed string/numeric values
            df["incident_zip"] = df["incident_zip"].astype(object)
            mask = np.random.rand(len(df)) < rate
            df.loc[mask, "incident_zip"] = df.loc[mask, "incident_zip"].astype(str) + "_STR"
        return df

    def inject_date_format_switch(self, df: pd.DataFrame, rate: float = 0.20) -> pd.DataFrame:
        df = df.copy()
        if "created_date" in df.columns:
            df["created_date"] = df["created_date"].astype(object)
            n_rows = len(df)
            cutoff = int(n_rows * (1 - rate))
            def _switch_format(val):
                try:
                    dt = pd.to_datetime(val)
                    return dt.strftime("%d/%m/%Y %I:%M:%S %p")
                except Exception:
                    return val
            df.iloc[cutoff:, df.columns.get_loc("created_date")] = (
                df.iloc[cutoff:]["created_date"].apply(_switch_format)
            )
        return df

    def inject_lat_long_swapped(self, df: pd.DataFrame, rate: float = 0.10) -> pd.DataFrame:
        df = df.copy()
        if "latitude" in df.columns and "longitude" in df.columns:
            df["latitude"] = df["latitude"].astype(object)
            df["longitude"] = df["longitude"].astype(object)
            mask = np.random.rand(len(df)) < rate
            temp_lat = df.loc[mask, "latitude"].copy()
            df.loc[mask, "latitude"] = df.loc[mask, "longitude"]
            df.loc[mask, "longitude"] = temp_lat
        return df

    def inject_exact_duplicates(self, df: pd.DataFrame, count: int = 15) -> pd.DataFrame:
        df = df.copy()
        if len(df) > count:
            dup_rows = df.sample(n=count, random_state=self.seed)
            df = pd.concat([df, dup_rows], ignore_index=True)
        return df

    def inject_near_duplicates(self, df: pd.DataFrame, count: int = 15) -> pd.DataFrame:
        df = df.copy()
        if len(df) > count:
            sample_rows = df.sample(n=count, random_state=self.seed).copy()
            sample_rows["descriptor"] = sample_rows["descriptor"].astype(object)
            sample_rows["created_date"] = sample_rows["created_date"].astype(object)
            for idx in sample_rows.index:
                if "descriptor" in sample_rows.columns and pd.notna(sample_rows.loc[idx, "descriptor"]):
                    sample_rows.loc[idx, "descriptor"] = str(sample_rows.loc[idx, "descriptor"]) + " "
                if "created_date" in sample_rows.columns:
                    try:
                        orig_dt = pd.to_datetime(sample_rows.loc[idx, "created_date"])
                        sample_rows.loc[idx, "created_date"] = (orig_dt + timedelta(seconds=3)).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        pass
            df = pd.concat([df, sample_rows], ignore_index=True)
        return df

    def inject_null_spike(self, df: pd.DataFrame, target_agency: str = "NYPD", null_rate: float = 0.85) -> pd.DataFrame:
        df = df.copy()
        if "agency" in df.columns and "descriptor" in df.columns:
            agency_mask = df["agency"] == target_agency
            spike_mask = agency_mask & (np.random.rand(len(df)) < null_rate)
            df.loc[spike_mask, "descriptor"] = np.nan
        return df

    def inject_closed_before_created(self, df: pd.DataFrame, rate: float = 0.10) -> pd.DataFrame:
        df = df.copy()
        if "created_date" in df.columns and "closed_date" in df.columns:
            df["created_date"] = df["created_date"].astype(str)
            df["closed_date"] = df["closed_date"].astype(str)
            
            n_corrupt = max(10, int(len(df) * rate))
            # Pick the first n_corrupt rows deterministically
            target_indices = df.index[:n_corrupt]
            
            # Explicitly force impossible chronological order
            df.loc[target_indices, "created_date"] = "2023-08-15 14:00:00"
            df.loc[target_indices, "closed_date"] = "2023-08-15 08:00:00"
        return df

    def inject_zip_borough_mismatch(self, df: pd.DataFrame, rate: float = 0.10) -> pd.DataFrame:
        df = df.copy()
        if "incident_zip" in df.columns and "borough" in df.columns:
            df["incident_zip"] = df["incident_zip"].astype(object)
            mask = np.random.rand(len(df)) < rate
            df.loc[mask, "incident_zip"] = "10301"
            df.loc[mask, "borough"] = "MANHATTAN"
        return df

    def inject_complaint_descriptor_mismatch(self, df: pd.DataFrame, rate: float = 0.10) -> pd.DataFrame:
        df = df.copy()
        if "complaint_type" in df.columns and "descriptor" in df.columns:
            mask = np.random.rand(len(df)) < rate
            df.loc[mask, "complaint_type"] = "Street Light Condition"
            df.loc[mask, "descriptor"] = "Loud Music/Party"
        return df

    def inject_resolution_status_contradiction(self, df: pd.DataFrame, rate: float = 0.10) -> pd.DataFrame:
        df = df.copy()
        if "status" in df.columns and "resolution_description" in df.columns:
            df["status"] = df["status"].astype(object)
            df["resolution_description"] = df["resolution_description"].astype(object)
            mask = np.random.rand(len(df)) < rate
            df.loc[mask, "status"] = "Open"
            df.loc[mask, "resolution_description"] = (
                "The Police Department responded to the complaint and with action taken, the condition was solved and closed."
            )
        return df

    def inject_pii_leak(self, df: pd.DataFrame, rate: float = 0.10) -> pd.DataFrame:
        df = df.copy()
        if "resolution_description" in df.columns:
            df["resolution_description"] = df["resolution_description"].astype(object)
            fake_pii_list = [
                " Call reporting party officer John Doe at 212-555-0199.",
                " Complainant email: citizen.jane99@gmail.com for follow-up.",
                " Contact resident Alice Smith at phone (917) 555-4321 immediately."
            ]
            mask = np.random.rand(len(df)) < rate
            for idx in df[mask].index:
                curr_text = str(df.loc[idx, "resolution_description"]) if pd.notna(df.loc[idx, "resolution_description"]) else ""
                df.loc[idx, "resolution_description"] = curr_text + random.choice(fake_pii_list)
        return df