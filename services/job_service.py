"""Business operations for searching and managing job listings."""
from typing import List, Optional

from core.database import session_scope
from core.models import Job
from core.repositories import JobRepository
from core.validators import check_text
from data.career_requirements import CAREERS

LEVELS = ["Internship", "Entry Level", "Junior", "Mid Level"]
CATEGORIES = list(CAREERS)


class JobService:
    """Validate job listing data and delegate listing operations to repositories."""

    EDITABLE_FIELDS = {"title", "company", "category", "level", "skills", "description", "location"}

    @staticmethod
    def search(query: str = "", category: str = "All", level: str = "All", only_open: bool = False) -> List[Job]:
        """Search listings by query and optional category, level, or open status."""
        with session_scope() as s:
            return JobRepository(s).search(query, category, level, only_open)

    @staticmethod
    def get(job_id: int) -> Optional[Job]:
        """Retrieve a listing by ID, or return ``None`` when it is absent."""
        with session_scope() as s:
            return JobRepository(s).get(job_id)

    @staticmethod
    def validate(title: str, company: str, category: str, level: str, skills: List[str], description: str) -> Optional[str]:
        """Return the first validation error for a listing, if one is found."""
        for err in (check_text(title, "Job title", 3, 140), check_text(company, "Company name", 2, 140)):
            if err:
                return err
        if not skills:
            return "Select at least one required skill."
        return check_text(description, "Description", 20, 2000)

    @staticmethod
    def create(data: dict, officer_id: int) -> Job:
        """Create an open, non-demo listing owned by a valid officer."""
        if officer_id <= 0:
            raise ValueError("A valid career officer account is required to create a listing.")
        with session_scope() as s:
            return JobRepository(s).add(Job(**data, is_demo=False, created_by=officer_id, is_open=True))

    @staticmethod
    def update(job_id: int, data: dict, officer_id: int) -> bool:
        """Update supported listing fields only when the officer may manage it."""
        if not data or not set(data).issubset(JobService.EDITABLE_FIELDS):
            raise ValueError("Listing updates contain unsupported fields.")
        with session_scope() as s:
            return JobRepository(s).update_manageable(job_id, officer_id, data)

    @staticmethod
    def set_open(job_id: int, is_open: bool, officer_id: int) -> bool:
        """Set a listing's open state when it belongs to the officer."""
        with session_scope() as s:
            return JobRepository(s).update_manageable(job_id, officer_id, {"is_open": is_open})

    @staticmethod
    def delete(job_id: int, officer_id: int) -> bool:
        """Delete a manageable listing and report whether it was removed."""
        with session_scope() as s:
            return JobRepository(s).delete_manageable(job_id, officer_id)
