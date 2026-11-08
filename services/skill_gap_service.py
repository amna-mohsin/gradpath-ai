"""Compare student skills with career and job skill requirements."""
from typing import Dict, List

from core.models import Student
from data.career_requirements import CAREERS, LEARNING_TIPS


class SkillGapService:
    """Calculate weighted career readiness and per-skill recommendations."""

    @staticmethod
    def analyze(student: Student, career: str) -> Dict:
        """Score career requirements and prioritize skills not yet available."""
        req = CAREERS[career]["skills"]
        have, learning = set(student.skill_list()), set(student.learning_list())
        rows: List[dict] = []
        earned = 0.0
        for skill, importance in req.items():
            if skill in have:
                status, credit, rec = "Available", 1.0, "Keep it sharp with a portfolio project."
            elif skill in learning:
                status, credit = "Needs improvement", 0.5
                rec = LEARNING_TIPS.get(skill, f"Finish your {skill} learning path and apply it in a mini-project.")
            else:
                status, credit = "Missing", 0.0
                rec = LEARNING_TIPS.get(skill, f"Start with a beginner course in {skill}, then build one small project.")
            earned += credit * importance
            rows.append({"skill": skill, "importance": importance, "status": status, "recommendation": rec})
        total = sum(req.values())
        gaps = sorted([r for r in rows if r["status"] != "Available"],
                      key=lambda r: (-r["importance"], r["status"] != "Missing"))
        return {
            "career": career, "match": round(100 * earned / total), "rows": rows,
            "priorities": gaps[:3], "projects": CAREERS[career]["projects"],
            "counts": {s: sum(1 for r in rows if r["status"] == s) for s in ("Available", "Needs improvement", "Missing")},
        }

    @staticmethod
    def match_job_skills(student: Student, job_skills: List[str]) -> int:
        """Return a percentage match, crediting skills in progress by half."""
        if not job_skills:
            return 0
        have, learning = set(student.skill_list()), set(student.learning_list())
        score = sum(1.0 if s in have else 0.5 if s in learning else 0.0 for s in job_skills)
        return round(100 * score / len(job_skills))
