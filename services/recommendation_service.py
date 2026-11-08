"""Recommendations.

ml_actions() is the model-driven part (counterfactual / what-if analysis): for each realistic
improvement we ask the SAME prediction model "what would this student's estimate be if they did
this?" and rank the improvements by the gain. next_actions() is the simple rule-based fallback.
"""
from types import SimpleNamespace
from typing import List

from core.config import CGPA_SCALE
from core.models import Job, Student
from services.prediction_service import PredictionResult, PredictorFactory
from services.skill_gap_service import SkillGapService

ACTIONS = {
    "CGPA": ("Lift your academic standing", "Target weaker courses next term and use office hours or study groups."),
    "Projects": ("Complete a portfolio project", "Build and publish 1-2 projects on GitHub with a clear README."),
    "Internships": ("Add relevant experience", "Apply for internships, virtual experience programmes or volunteer tech work."),
    "Technical skills": ("Strengthen a required technical skill", "Open Skill-Gap Analysis and pick the top missing skill."),
    "Certifications": ("Earn a recognised certification", "Choose one aligned with your target career and finish it in 4-6 weeks."),
    "Communication": ("Practise communication and interviews", "Do a mock interview and record a 2-minute project pitch."),
    "Extracurricular": ("Join a society or lead an activity", "Leadership and teamwork show up strongly in interviews."),
}


def _n(value) -> float:
    """Treat missing numeric profile values as zero."""
    return value or 0


# Each scenario: when it is realistic, and which profile numbers it changes.
SCENARIOS = [
    dict(factor="Projects", title="Complete 2 more projects",
         detail="Build and publish two portfolio projects, each with a clear README and a short demo.",
         can=lambda s: _n(s.projects) < 9, change=lambda s: {"projects": _n(s.projects) + 2}),
    dict(factor="Internships", title="Complete an internship",
         detail="Apply for internships or virtual experience programmes. Even one counts as real experience.",
         can=lambda s: _n(s.internships) == 0, change=lambda s: {"internships": 1}),
    dict(factor="Communication", title="Raise communication by 2 points",
         detail="Do mock interviews, present your projects to friends, and practise writing clearly.",
         can=lambda s: _n(s.communication) <= 8, change=lambda s: {"communication": min(10, _n(s.communication) + 2)}),
    dict(factor="Extracurricular", title="Take a leadership or society role",
         detail="Lead a club activity, organise an event, or join a competition team.",
         can=lambda s: _n(s.extracurricular) <= 7, change=lambda s: {"extracurricular": min(10, _n(s.extracurricular) + 3)}),
    dict(factor="CGPA", title="Raise your CGPA by 0.2",
         detail="Focus on the courses where you are weakest and use office hours or study groups.",
         can=lambda s: _n(s.cgpa) + 0.2 <= CGPA_SCALE, change=lambda s: {"cgpa": round(_n(s.cgpa) + 0.2, 2)}),
]


def _what_if(student, **over):
    """Build an unsaved student-like object with selected profile values replaced."""
    base = dict(cgpa=_n(student.cgpa), projects=_n(student.projects), internships=_n(student.internships),
                communication=_n(student.communication), extracurricular=_n(student.extracurricular))
    base.update(over)
    return SimpleNamespace(**base, skill_list=student.skill_list, learning_list=student.learning_list,
                           cert_list=student.cert_list)


class RecommendationService:
    """Rank profile improvements and job listings using prediction and skill matches."""

    @staticmethod
    def ml_actions(student, limit: int = 4) -> dict:
        """Compare feasible profile changes with a baseline and rank positive gains."""
        predictor = PredictorFactory.create()
        base = predictor.predict(student)
        found = []
        for sc in SCENARIOS:
            if not sc["can"](student):
                continue
            change = sc["change"](student)
            new = predictor.predict(_what_if(student, **change))
            gain = round(new.probability - base.probability, 1)
            if gain > 0:
                found.append(dict(title=sc["title"], detail=sc["detail"], factor=sc["factor"], gain=gain,
                                  new_probability=new.probability, new_category=new.category,
                                  moves_up=new.category != base.category, change=change))
        found.sort(key=lambda r: -r["gain"])
        top = found[:limit]
        combined = None
        if len(top) >= 2:
            merged = {}
            for item in top[:3]:
                merged.update(item["change"])
            combined = predictor.predict(_what_if(student, **merged))
        return {"baseline": base, "items": top, "combined": combined, "is_ml": base.is_ml,
                "combined_titles": [i["title"] for i in top[:3]]}

    @staticmethod
    def next_actions(result: PredictionResult, limit: int = 4) -> List[dict]:
        """Rank rule-based improvement suggestions by weighted factor weakness."""
        ranked = sorted(result.factors, key=lambda f: -(f["weight"] * (100 - f["score"])))
        return [{"title": ACTIONS[f["name"]][0], "detail": ACTIONS[f["name"]][1], "factor": f["name"]}
                for f in ranked if f["score"] < 85][:limit]

    @staticmethod
    def rank_jobs(student: Student, jobs: List[Job]) -> List[tuple]:
        """Sort jobs by the student's match against each listing's required skills."""
        scored = [(j, SkillGapService.match_job_skills(student, j.skill_list())) for j in jobs]
        return sorted(scored, key=lambda x: -x[1])