"""Student profile persistence, validation, and activity-log operations."""
from typing import List, Optional

from core.config import CGPA_SCALE
from core.database import session_scope
from core.models import ActivityLog, Student, User
from core.repositories import ActivityRepository, StudentRepository
from core.validators import check_name, check_phone, check_text, check_url, clean_phone


class StudentService:
    """Retrieve, validate, and update student profile records."""

    @staticmethod
    def get(student_id: int) -> Optional[Student]:
        """Retrieve a student by ID, or return ``None`` if absent."""
        with session_scope() as s:
            return StudentRepository(s).get(student_id)

    @staticmethod
    def list_students(include_demo: bool = True) -> List[Student]:
        """List students, optionally excluding fictional demo accounts."""
        with session_scope() as s:
            return StudentRepository(s).list_students(include_demo)

    @staticmethod
    def update_profile(student_id: int, data: dict) -> Optional[Student]:
        """Save profile changes and invalidate the cached report snapshot."""
        with session_scope() as s:
            student = StudentRepository(s).update(student_id, data)
        if student:
            from services.report_service import ReportService
            ReportService.snapshot.clear()
        return student

    @staticmethod
    def validate_profile(d: dict) -> List[str]:
        """Return all validation errors found in profile form data."""
        errors = [e for e in (
            check_name(d.get("name", "")), check_phone(d.get("phone", ""), True),
            check_text(d.get("city", ""), "City", 2, 60), check_text(d.get("university", ""), "University", 3, 120),
            check_url(d.get("portfolio_url", ""))) if e]
        if not d.get("degree"):
            errors.append("Please choose your degree.")
        if not d.get("department"):
            errors.append("Please choose your department.")
        cgpa = d.get("cgpa") or 0
        if cgpa <= 0 or cgpa > CGPA_SCALE:
            errors.append(f"CGPA must be greater than 0 and at most {CGPA_SCALE:g}.")
        if not d.get("skills"):
            errors.append("Select at least one skill you are confident in.")
        if not d.get("target_career"):
            errors.append("Please choose a target career.")
        if any(len(c) > 80 for c in d.get("certifications", [])):
            errors.append("Each certification name must be at most 80 characters.")
        return errors

    @staticmethod
    def to_record(d: dict) -> dict:
        """Normalize profile form values into fields for persistence."""
        skills = list(d["skills"])
        learning = [s for s in d.get("learning", []) if s not in skills]
        return dict(
            name=d["name"].strip(), phone=clean_phone(d["phone"]), city=d["city"].strip(),
            university=d["university"].strip(), degree=d["degree"], department=d["department"],
            graduation_year=int(d["graduation_year"]), cgpa=float(d["cgpa"]), skills=",".join(skills),
            learning_skills=",".join(learning), target_career=d["target_career"], projects=int(d["projects"]),
            internships=int(d["internships"]), work_experience_months=int(d["months"]),
            certifications=",".join(c.strip() for c in d.get("certifications", []) if c.strip()),
            portfolio_url=(d.get("portfolio_url") or "").strip(), communication=int(d["communication"]),
            extracurricular=int(d["extracurricular"]))


class ActivityService:
    """Record and retrieve recent user activity."""

    @staticmethod
    def log(user: User, action: str, detail: str = "") -> None:
        """Save an activity entry with its detail limited to 300 characters."""
        with session_scope() as s:
            ActivityRepository(s).add(ActivityLog(user_id=user.id, actor_name=user.name,
                                                  action=action, detail=detail[:300]))

    @staticmethod
    def recent(user_id: Optional[int] = None, limit: int = 6) -> List[ActivityLog]:
        """Return recent activity, optionally limited to one user."""
        with session_scope() as s:
            return ActivityRepository(s).recent(user_id, limit)

    @staticmethod
    def recent_profiles(limit: int = 6) -> List[ActivityLog]:
        """Return recent profile-creation activity for the officer overview."""
        with session_scope() as s:
            return ActivityRepository(s).recent_profiles(limit)
