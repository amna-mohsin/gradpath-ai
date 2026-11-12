"""Domain model (SQLAlchemy ORM).

OOAD notes
- Inheritance : Student and CareerOfficer inherit from User (joined-table inheritance).
- Composition : Student -> CareerGoal -> GoalTask (children are deleted with their parent).
- Aggregation : CareerOfficer o-- Job (jobs survive if the officer is removed).
- Association : JobApplication is the association class between Student and Job;
                Student 1..* PlacementPrediction.
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def split_csv(value: Optional[str]) -> List[str]:
    """Convert a comma-separated database field into trimmed, non-empty values."""
    return [x.strip() for x in (value or "").split(",") if x.strip()]


def utcnow() -> datetime:
    """Provide the UTC timestamp used as the default for persisted records."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    """Shared SQLAlchemy declarative base for all application tables."""
    pass


class User(Base):
    """Shared account fields and polymorphic base for students and officers."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __mapper_args__ = {
        "polymorphic_on": "role",
        "polymorphic_identity": "user",
        "with_polymorphic": "*",
    }

    @property
    def initials(self) -> str:
        """Return uppercase initials for the account name."""
        parts = (self.name or "?").split()
        return "".join(p[0] for p in parts[:2]).upper()

    @property
    def first_name(self) -> str:
        """Return the account holder's first name for personalized greetings."""
        return (self.name or "there").split()[0]

    def display_role(self) -> str:
        """Return the generic role label overridden by each account subtype."""
        return "User"


class Student(User):
    """Student account, academic profile, readiness inputs, and career goals."""
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    university: Mapped[str] = mapped_column(String(160), default="")
    degree: Mapped[str] = mapped_column(String(40), default="")
    department: Mapped[str] = mapped_column(String(80), default="")
    graduation_year: Mapped[int] = mapped_column(Integer, default=2027)
    cgpa: Mapped[float] = mapped_column(Float, default=0.0)
    skills: Mapped[str] = mapped_column(Text, default="")            # confident skills (CSV)
    learning_skills: Mapped[str] = mapped_column(Text, default="")   # skills being learned (CSV)
    certifications: Mapped[str] = mapped_column(Text, default="")
    projects: Mapped[int] = mapped_column(Integer, default=0)
    internships: Mapped[int] = mapped_column(Integer, default=0)
    work_experience_months: Mapped[int] = mapped_column(Integer, default=0)
    communication: Mapped[int] = mapped_column(Integer, default=0)      # 1-10
    extracurricular: Mapped[int] = mapped_column(Integer, default=0)    # 0-10
    target_career: Mapped[str] = mapped_column(String(80), default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    phone: Mapped[str] = mapped_column(String(30), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    portfolio_url: Mapped[str] = mapped_column(String(200), default="")

    goals: Mapped[List["CareerGoal"]] = relationship(
        back_populates="student", cascade="all, delete-orphan",
        lazy="selectin", order_by="CareerGoal.id",
    )

    __mapper_args__ = {"polymorphic_identity": "student"}

    def display_role(self) -> str:
        """Return the student-facing role label."""
        return "Student"

    def skill_list(self) -> List[str]:
        """Return the student's confident skills as a normalized list."""
        return split_csv(self.skills)

    def learning_list(self) -> List[str]:
        """Return the student's in-progress skills as a normalized list."""
        return split_csv(self.learning_skills)

    def cert_list(self) -> List[str]:
        """Return the student's certifications as a normalized list."""
        return split_csv(self.certifications)

    @property
    def is_onboarded(self) -> bool:
        """True once the student has filled in the essentials (used to gate the main app)."""
        return bool(self.university and self.department and (self.cgpa or 0) > 0
                    and self.skill_list() and self.target_career and (self.communication or 0) > 0)

    def profile_completion(self) -> int:
        """Calculate the percentage of profile fields completed by the student."""
        checks = [
            bool(self.name), bool(self.university), bool(self.degree), bool(self.department),
            bool(self.graduation_year), (self.cgpa or 0) > 0, bool(self.skill_list()),
            bool(self.cert_list()), bool(self.target_career), (self.communication or 0) > 0,
            (self.projects or 0) > 0 or (self.internships or 0) > 0, bool(self.phone), bool(self.city),
        ]
        return round(100 * sum(checks) / len(checks))


class CareerOfficer(User):
    """Career-office account and its associated office name."""
    __tablename__ = "career_officers"

    id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    office: Mapped[str] = mapped_column(String(120), default="University Career Office")

    # AGGREGATION: an officer has jobs, but jobs can exist without the officer (no cascade delete).
    # foreign() maps the existing jobs.created_by column, so no database migration is needed.
    jobs: Mapped[List["Job"]] = relationship(
        primaryjoin="CareerOfficer.id == foreign(Job.created_by)",
        back_populates="creator", lazy="select",
    )

    __mapper_args__ = {"polymorphic_identity": "officer"}

    def display_role(self) -> str:
        """Return the career-officer role label."""
        return "Career Officer"


class AuthSession(Base):
    """Hashed browser-session token and expiry for persistent authentication."""
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Job(Base):
    """Job listing, including its creator, visibility, and applications."""
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(140))
    company: Mapped[str] = mapped_column(String(140))
    category: Mapped[str] = mapped_column(String(80))
    level: Mapped[str] = mapped_column(String(40))
    skills: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(String(120), default="")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    applications: Mapped[List["JobApplication"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", lazy="select")
    creator: Mapped[Optional["CareerOfficer"]] = relationship(
        primaryjoin="foreign(Job.created_by) == CareerOfficer.id",
        back_populates="jobs", lazy="joined",
    )

    def skill_list(self) -> List[str]:
        """Return required job skills as a normalized list."""
        return split_csv(self.skills)


class CareerGoal(Base):
    """Student-owned career goal with cascading tasks and completion progress."""
    __tablename__ = "career_goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    student: Mapped["Student"] = relationship(back_populates="goals")
    tasks: Mapped[List["GoalTask"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan",
        lazy="selectin", order_by="GoalTask.id",
    )

    @property
    def progress(self) -> int:
        """Calculate the completed-task percentage, or zero when no tasks exist."""
        if not self.tasks:
            return 0
        return round(100 * sum(1 for t in self.tasks if t.done) / len(self.tasks))


class GoalTask(Base):
    """A single actionable task belonging to a career goal."""
    __tablename__ = "goal_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("career_goals.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    goal: Mapped["CareerGoal"] = relationship(back_populates="tasks")


class PlacementPrediction(Base):
    """Saved readiness estimate and model label for a student."""
    __tablename__ = "placement_predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    probability: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(40))
    model_name: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ActivityLog(Base):
    """Audit-style activity event shown in relevant application summaries."""
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    actor_name: Mapped[str] = mapped_column(String(120), default="")
    action: Mapped[str] = mapped_column(String(80))
    detail: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class JobApplication(Base):
    """A student's application to a job (association class between Student and Job)."""
    __tablename__ = "job_applications"
    __table_args__ = (UniqueConstraint("job_id", "student_id", name="uq_application_job_student"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    phone: Mapped[str] = mapped_column(String(30), default="")
    portfolio_url: Mapped[str] = mapped_column(String(200), default="")
    availability: Mapped[str] = mapped_column(String(60), default="")
    cover_note: Mapped[str] = mapped_column(Text, default="")
    resume_text: Mapped[str] = mapped_column(Text, default="")
    # deferred: the PDF bytes are only fetched when explicitly requested, not with every application list
    resume_pdf: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True, deferred=True)
    skill_match: Mapped[int] = mapped_column(Integer, default=0)
    resume_match: Mapped[int] = mapped_column(Integer, default=0)
    readiness_category: Mapped[str] = mapped_column(String(40), default="")
    readiness_pct: Mapped[float] = mapped_column(Float, default=0.0)
    fit_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    status: Mapped[str] = mapped_column(String(30), default="Submitted")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    job: Mapped["Job"] = relationship(back_populates="applications", lazy="joined")
    student: Mapped["Student"] = relationship(lazy="joined")


class Message(Base):
    """Direct message between a student and a career officer."""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    body: Mapped[str] = mapped_column(Text)
    # Optional link to the job a message is about (maps the existing job_id column; no migration).
    job: Mapped[Optional["Job"]] = relationship(
        primaryjoin="foreign(Message.job_id) == Job.id", lazy="select", viewonly=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
