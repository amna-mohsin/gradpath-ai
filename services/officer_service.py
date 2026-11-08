"""Profile updates for career officer accounts."""
from typing import Optional, Tuple

from core.database import session_scope
from core.models import CareerOfficer
from core.repositories import UserRepository
from core.validators import check_name, check_text


class OfficerService:
    """Validate and persist career officer profile changes."""

    @staticmethod
    def update_profile(officer_id: int, name: str, office: str) -> Tuple[Optional[CareerOfficer], str]:
        """Update a matching officer's name and office, or return a validation error."""
        for error in (check_name(name), check_text(office, "Company / office name", 3, 120)):
            if error:
                return None, error
        with session_scope() as session:
            officer = UserRepository(session).get(officer_id)
            if not isinstance(officer, CareerOfficer):
                return None, "Career officer account not found."
            officer.name = name.strip()
            officer.office = office.strip()
            session.flush()
            return officer, ""
