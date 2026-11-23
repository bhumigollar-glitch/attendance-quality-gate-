import datetime
from typing import Optional
import pandas as pd
from app.rules.base import BaseRuleSet


class CleanerService:
    """
    Applies conservative data cleaning transformations strictly to accepted datasets.
    Never invents missing data. Only applies deterministic normalizations:
    1. Trims leading and trailing whitespace.
    2. Normalizes dates into standard ISO format (YYYY-MM-DD).
    3. Standardizes status casing to Title Case (e.g. 'Present', 'Absent', 'Leave').
    """

    @classmethod
    def clean(cls, df: pd.DataFrame, rule_set: BaseRuleSet) -> pd.DataFrame:
        cleaned_df = df.copy()

        # 1. Trim whitespace on all text columns
        for col in cleaned_df.columns:
            cleaned_df[col] = cleaned_df[col].astype(str).apply(lambda x: x.strip())

        # 2. Normalize attendance_status to Title Case
        if "attendance_status" in cleaned_df.columns:
            cleaned_df["attendance_status"] = cleaned_df["attendance_status"].apply(
                lambda val: val.title() if val else val
            )

        # 3. Normalize attendance_date to YYYY-MM-DD
        if "attendance_date" in cleaned_df.columns:
            cleaned_df["attendance_date"] = cleaned_df["attendance_date"].apply(
                lambda val: cls._normalize_date(val, rule_set)
            )

        return cleaned_df

    @staticmethod
    def _normalize_date(date_str: str, rule_set: BaseRuleSet) -> str:
        """Parse date string according to rule set formats and return ISO YYYY-MM-DD."""
        if not date_str:
            return ""
        val = date_str.strip()
        for fmt in rule_set.allowed_date_formats:
            try:
                dt = datetime.datetime.strptime(val, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        # If already formatted or fallback
        return val
