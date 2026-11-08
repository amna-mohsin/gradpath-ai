"""Job applications: validation, fit scoring and officer-side ranking."""
from typing import List, Tuple

from core.database import session_scope
from core.models import ActivityLog, Job, JobApplication, Student
from core.repositories import ActivityRepository, ApplicationRepository, JobRepository
from core.validators import check_phone, check_text, check_url, clean_phone
from services.prediction_service import PredictionService
from services.resume_service import ResumeService
from services.skill_gap_service import SkillGapService

STATUSES = ["Submitted", "Under review", "Shortlisted", "Interview", "Offer", "Not selected"]
AVAILABILITY = ["Immediately", "Within 1 month", "After graduation", "Part-time only"]
READINESS_INDEX = {"Job Ready": 100, "Developing": 60, "Needs Improvement": 25}
W_SKILL, W_RESUME, W_READY = 0.55, 0.25, 0.20


def fit_label(score: int) -> Tuple[str, str]:
    """Map an application fit score to its display label and status kind."""
    if score >= 75:
        return "Strong fit", "success"
    if score >= 55:
        return "Good fit", "info"
    if score >= 35:
        return "Partial fit", "warn"
    return "Low fit", "danger"


def status_kind(status: str) -> str:
    """Return the display kind used for an application status badge."""
    return {"Shortlisted": "success", "Interview": "success", "Offer": "success",
            "Under review": "info", "Not selected": "danger"}.get(status, "neutral")


class ApplicationService:
    """Validate, score, submit, and manage job applications."""

    @staticmethod
    def compute_fit(student: Student, job: Job, resume_text: str) -> dict:
        """Calculate a weighted fit score from skills, resume keywords, and readiness."""
        skill_match = SkillGapService.match_job_skills(student, job.skill_list())
        resume_match = ResumeService.skill_coverage(resume_text, job.skill_list())
        res = PredictionService.estimate(student)
        ready = READINESS_INDEX.get(res.category, 25)
        fit = round(W_SKILL * skill_match + W_RESUME * resume_match + W_READY * ready)
        return {"skill_match": skill_match, "resume_match": resume_match, "readiness_category": res.category,
                "readiness_pct": res.probability, "fit_score": fit}

    @staticmethod
    def validate(d: dict) -> List[str]:
        """Return validation errors for an application form, if any."""
        portfolio_url = (d.get("portfolio_url") or "").strip()
        errors = [e for e in (check_phone(d.get("phone", "")),
                              check_url(portfolio_url) if portfolio_url else
                              "Please provide at least one portfolio, GitHub or LinkedIn link.",
                              check_text(d.get("cover_note", ""), "Cover note", 50, 1500)) if e]
        if len((d.get("resume_text") or "").split()) < 40:
            errors.append("Please upload a readable PDF resume containing at least 40 words.")
        if not (d.get("resume_pdf") or b"").startswith(b"%PDF-"):
            errors.append("Please upload a valid PDF resume.")
        if not d.get("availability"):
            errors.append("Please choose your availability.")
        if not d.get("consent"):
            errors.append("Please confirm that your details are accurate and can be shared with the Career Office.")
        return errors

    @staticmethod
    def apply(student: Student, job_id: int, d: dict) -> Tuple[bool, str]:
        """Validate and save an application, rejecting closed jobs and duplicates."""
        errors = ApplicationService.validate(d)
        if errors:
            return False, errors[0]
        with session_scope() as s:
            job = JobRepository(s).get(job_id)
            if not job or not job.is_open:
                return False, "This position is no longer open."
            apps = ApplicationRepository(s)
            if apps.find(job_id, student.id):
                return False, "You have already applied to this job."
            fit = ApplicationService.compute_fit(student, job, d["resume_text"])
            apps.add(JobApplication(job_id=job_id, student_id=student.id, phone=clean_phone(d["phone"]),
                                    portfolio_url=(d.get("portfolio_url") or "").strip(),
                                    availability=d["availability"], cover_note=d["cover_note"].strip(),
                                    resume_text=d["resume_text"].strip(), resume_pdf=d["resume_pdf"],
                                    status="Submitted", **fit))
            ActivityRepository(s).add(ActivityLog(user_id=student.id, actor_name=student.name,
                                                  action="Applied for a job", detail=f"{job.title} at {job.company}"))
            return True, f'Application sent for "{job.title}".'

    @staticmethod
    def for_job(job_id: int) -> List[JobApplication]:
        """Return applications for a job in repository-defined ranking order."""
        with session_scope() as s:
            return ApplicationRepository(s).for_job(job_id)

    @staticmethod
    def for_student(student_id: int) -> List[JobApplication]:
        """Return all applications submitted by a student."""
        with session_scope() as s:
            return ApplicationRepository(s).for_student(student_id)

    @staticmethod
    def applied_job_ids(student_id: int) -> set:
        """Return the job IDs to which the student has already applied."""
        return {a.job_id for a in ApplicationService.for_student(student_id)}

    @staticmethod
    def counts() -> dict:
        """Return the number of applications received by each job."""
        with session_scope() as s:
            return ApplicationRepository(s).counts_by_job()

    @staticmethod
    def all_applications() -> List[JobApplication]:
        """Return every stored application."""
        with session_scope() as s:
            return ApplicationRepository(s).everything()

    @staticmethod
    def update_status(app_id: int, status: str) -> None:
        """Update an application's status when the requested value is supported."""
        with session_scope() as s:
            app = ApplicationRepository(s).get(app_id)
            if app and status in STATUSES:
                app.status = status
