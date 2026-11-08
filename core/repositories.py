"""Repository pattern: all SQL lives here. Services never write queries directly."""
from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session

from core.models import (ActivityLog, AuthSession, CareerGoal, CareerOfficer, GoalTask, Job, JobApplication,
                         Message, PlacementPrediction, Student, User)

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Provide shared CRUD operations for a SQLAlchemy model and session."""
    model: Type[T]

    def __init__(self, session: Session):
        """Bind the repository to the caller's transaction-scoped session."""
        self.s = session

    def get(self, obj_id: int) -> Optional[T]:
        """Load one record by its primary key."""
        return self.s.get(self.model, obj_id)

    def all(self) -> List[T]:
        """Return every record for the repository's model."""
        return list(self.s.scalars(select(self.model)))

    def add(self, obj: T) -> T:
        """Stage and flush a new record, returning it with its generated fields."""
        self.s.add(obj)
        self.s.flush()
        return obj

    def delete(self, obj: T) -> None:
        """Mark a record for deletion in the current transaction."""
        self.s.delete(obj)

    def count(self) -> int:
        """Return the number of records for this model."""
        return self.s.scalar(select(func.count()).select_from(self.model)) or 0


class UserRepository(BaseRepository[User]):
    """Look up user accounts and list registered account subtypes."""
    model = User

    def by_email(self, email: str) -> Optional[User]:
        """Find an account by email without regard to letter case."""
        return self.s.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))

    def officers(self) -> List[CareerOfficer]:
        """Return career officers ordered by name."""
        return list(self.s.scalars(select(CareerOfficer).order_by(CareerOfficer.name)))

    def registered_students(self) -> List[Student]:
        """Students who can actually sign in (demo seed students have no password)."""
        return list(self.s.scalars(select(Student).where(Student.password_hash.is_not(None)).order_by(Student.name)))


class AuthSessionRepository(BaseRepository[AuthSession]):
    """Persist and query browser-session authentication records."""
    model = AuthSession

    def by_token_hash(self, token_hash: str) -> Optional[AuthSession]:
        """Find a session by its stored token hash."""
        return self.s.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))

    def delete_for_user(self, user_id: int) -> None:
        """Remove every persistent login session belonging to an account."""
        for auth_session in self.s.scalars(select(AuthSession).where(AuthSession.user_id == user_id)):
            self.s.delete(auth_session)


class StudentRepository(BaseRepository[Student]):
    """Query and update student profiles."""
    model = Student

    def list_students(self, include_demo: bool = True) -> List[Student]:
        """Return students by name, optionally excluding fictional demo records."""
        q = select(Student).order_by(Student.name)
        if not include_demo:
            q = q.where(Student.is_demo.is_(False))
        return list(self.s.scalars(q))

    def update(self, student_id: int, data: dict) -> Optional[Student]:
        """Apply validated profile fields to a student and flush the update."""
        student = self.get(student_id)
        if student:
            for key, value in data.items():
                setattr(student, key, value)
            self.s.flush()
        return student


class JobRepository(BaseRepository[Job]):
    """Search job listings and enforce creator ownership on listing changes."""
    model = Job

    def get_manageable(self, job_id: int, officer_id: int) -> Optional[Job]:
        """Return a non-demo listing only when it belongs to the given officer."""
        return self.s.scalar(select(Job).where(
            Job.id == job_id,
            Job.created_by == officer_id,
            Job.is_demo.is_(False),
        ))

    def search(self, query: str = "", category: str = "All", level: str = "All",
               only_open: bool = False) -> List[Job]:
        """Filter listings by text, career category, level, and open status."""
        q = select(Job).order_by(Job.created_at.desc(), Job.id.desc())
        if only_open:
            q = q.where(Job.is_open.is_(True))
        if query.strip():
            like = f"%{query.strip().lower()}%"
            q = q.where(or_(func.lower(Job.title).like(like), func.lower(Job.company).like(like)))
        if category != "All":
            q = q.where(Job.category == category)
        if level != "All":
            q = q.where(Job.level == level)
        return list(self.s.scalars(q))

    def update_manageable(self, job_id: int, officer_id: int, data: dict) -> bool:
        """Update an officer-owned listing and report whether it was authorized."""
        job = self.get_manageable(job_id, officer_id)
        if not job:
            return False
        for key, value in data.items():
            setattr(job, key, value)
        self.s.flush()
        return True

    def delete_manageable(self, job_id: int, officer_id: int) -> bool:
        """Delete an officer-owned listing and its dependent applications."""
        job = self.get_manageable(job_id, officer_id)
        if not job:
            return False
        self.s.delete(job)
        return True


class GoalRepository(BaseRepository[CareerGoal]):
    """Read career goals and manage their child tasks."""
    model = CareerGoal

    def for_student(self, student_id: int) -> List[CareerGoal]:
        """Return a student's goals in creation order."""
        q = select(CareerGoal).where(CareerGoal.student_id == student_id).order_by(CareerGoal.id)
        return list(self.s.scalars(q))

    def add_task(self, goal_id: int, title: str) -> GoalTask:
        """Create and flush a task belonging to a career goal."""
        task = GoalTask(goal_id=goal_id, title=title)
        self.s.add(task)
        self.s.flush()
        return task

    def toggle_task(self, task_id: int) -> None:
        """Switch a task between complete and incomplete when it exists."""
        task = self.s.get(GoalTask, task_id)
        if task:
            task.done = not task.done

    def delete_task(self, task_id: int) -> None:
        """Delete a task when the requested task exists."""
        task = self.s.get(GoalTask, task_id)
        if task:
            self.s.delete(task)


class PredictionRepository(BaseRepository[PlacementPrediction]):
    """Retrieve saved readiness predictions for a student."""
    model = PlacementPrediction

    def latest(self, student_id: int) -> Optional[PlacementPrediction]:
        """Return the most recently saved prediction, if one exists."""
        q = (select(PlacementPrediction).where(PlacementPrediction.student_id == student_id)
             .order_by(PlacementPrediction.id.desc()).limit(1))
        return self.s.scalar(q)

    def history(self, student_id: int) -> List[PlacementPrediction]:
        """Return a student's saved predictions from oldest to newest."""
        q = (select(PlacementPrediction).where(PlacementPrediction.student_id == student_id)
             .order_by(PlacementPrediction.id))
        return list(self.s.scalars(q))


class ActivityRepository(BaseRepository[ActivityLog]):
    """Read recent activity and profile-creation events."""
    model = ActivityLog

    def recent(self, user_id: Optional[int] = None, limit: int = 6) -> List[ActivityLog]:
        """Return recent events globally or limited to one account."""
        q = select(ActivityLog).order_by(ActivityLog.id.desc()).limit(limit)
        if user_id is not None:
            q = q.where(ActivityLog.user_id == user_id)
        return list(self.s.scalars(q))

    def recent_profiles(self, limit: int = 6) -> List[ActivityLog]:
        """Return recent profile-created or profile-completed events only."""
        q = (select(ActivityLog).where(ActivityLog.action.in_(("Profile created", "Profile completed")))
             .order_by(ActivityLog.id.desc()).limit(limit))
        return list(self.s.scalars(q))


class ApplicationRepository(BaseRepository[JobApplication]):
    """Query job applications by job, student, and ranking."""
    model = JobApplication

    def for_job(self, job_id: int) -> List[JobApplication]:
        """Return applications for a job ranked by fit score."""
        q = (select(JobApplication).where(JobApplication.job_id == job_id)
             .order_by(JobApplication.fit_score.desc(), JobApplication.created_at))
        return list(self.s.scalars(q))

    def for_student(self, student_id: int) -> List[JobApplication]:
        """Return a student's applications from newest to oldest."""
        q = (select(JobApplication).where(JobApplication.student_id == student_id)
             .order_by(JobApplication.created_at.desc()))
        return list(self.s.scalars(q))

    def find(self, job_id: int, student_id: int) -> Optional[JobApplication]:
        """Find the unique application for a student and job pair."""
        return self.s.scalar(select(JobApplication).where(
            JobApplication.job_id == job_id, JobApplication.student_id == student_id))

    def counts_by_job(self) -> dict:
        """Return application counts keyed by job ID."""
        rows = self.s.execute(select(JobApplication.job_id, func.count()).group_by(JobApplication.job_id))
        return {job_id: n for job_id, n in rows}

    def everything(self) -> List[JobApplication]:
        """Return every application ordered from highest to lowest fit."""
        return list(self.s.scalars(select(JobApplication).order_by(JobApplication.fit_score.desc())))


class MessageRepository(BaseRepository[Message]):
    """Retrieve message threads and update read state."""
    model = Message

    def involving(self, user_id: int) -> List[Message]:
        """Return all messages sent or received by one account."""
        q = select(Message).where(or_(Message.sender_id == user_id, Message.recipient_id == user_id)).order_by(Message.id)
        return list(self.s.scalars(q))

    def between(self, a: int, b: int) -> List[Message]:
        """Return a conversation in chronological order between two accounts."""
        q = select(Message).where(or_(and_(Message.sender_id == a, Message.recipient_id == b),
                                      and_(Message.sender_id == b, Message.recipient_id == a))).order_by(Message.id)
        return list(self.s.scalars(q))

    def mark_read(self, me: int, other: int) -> None:
        """Mark messages from the other account as read by the current account."""
        self.s.execute(update(Message).where(Message.recipient_id == me, Message.sender_id == other,
                                             Message.is_read.is_(False)).values(is_read=True))

    def unread_count(self, user_id: int) -> int:
        """Count unread messages addressed to the specified account."""
        return self.s.scalar(select(func.count()).select_from(Message).where(
            Message.recipient_id == user_id, Message.is_read.is_(False))) or 0
