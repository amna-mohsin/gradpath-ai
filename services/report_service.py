"""Builds analytics DataFrames from the real database records."""
from collections import Counter
from dataclasses import dataclass

import pandas as pd
import streamlit as st

from data.career_requirements import DEPARTMENT_DEFAULT_CAREER
from services.prediction_service import PredictorFactory
from services.skill_gap_service import SkillGapService
from services.student_service import StudentService


@dataclass
class Snapshot:
    """Bundle report tables with the name of the estimator used."""

    students: pd.DataFrame
    gaps: pd.DataFrame
    model_name: str


class ReportService:
    """Build cached student and skill-gap report data for officer views."""

    @staticmethod
    @st.cache_data(ttl=15, show_spinner=False)
    def snapshot(include_demo: bool = True) -> Snapshot:
        """Create a report snapshot from onboarded students and their skill gaps."""
        predictor = PredictorFactory.create()
        rows, gap_counter = [], Counter()
        for st_ in StudentService.list_students(include_demo):
            if not st_.is_onboarded:      # skip brand-new accounts with no profile yet
                continue
            res = predictor.predict(st_)
            career = st_.target_career or DEPARTMENT_DEFAULT_CAREER.get(st_.department, "Software Developer")
            for r in SkillGapService.analyze(st_, career)["rows"]:
                if r["status"] != "Available":
                    gap_counter[r["skill"]] += 1
            rows.append({
                "ID": st_.id, "Name": st_.name, "Department": st_.department or "Not set",
                "CGPA": round(st_.cgpa or 0, 2), "Skills": ", ".join(st_.skill_list()),
                "Internships": st_.internships or 0, "Projects": st_.projects or 0,
                "Target Career": career, "Readiness": res.category, "Estimate (%)": res.probability,
                "Source": "Demo (fictional)" if st_.is_demo else "Registered",
            })
        cols = ["ID", "Name", "Department", "CGPA", "Skills", "Internships", "Projects",
                "Target Career", "Readiness", "Estimate (%)", "Source"]
        df = pd.DataFrame(rows, columns=cols)
        gaps = pd.DataFrame(gap_counter.most_common(10), columns=["Skill", "Students with gap"])
        return Snapshot(df, gaps, predictor.name)

    @staticmethod
    def to_csv(df: pd.DataFrame) -> bytes:
        """Serialize a DataFrame as UTF-8 CSV bytes without its index."""
        return df.to_csv(index=False).encode("utf-8")
