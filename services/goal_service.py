"""Database operations and summaries for student career goals and tasks."""
from typing import List

from core.database import session_scope
from core.models import CareerGoal
from core.repositories import GoalRepository


class GoalService:
    """Create, retrieve, update, and summarize career goals."""

    @staticmethod
    def list_goals(student_id: int) -> List[CareerGoal]:
        """Return the goals belonging to a student."""
        with session_scope() as s:
            return GoalRepository(s).for_student(student_id)

    @staticmethod
    def create_goal(student_id: int, title: str, description: str = "") -> CareerGoal:
        """Create a goal after trimming its title and description."""
        with session_scope() as s:
            return GoalRepository(s).add(CareerGoal(student_id=student_id, title=title.strip(), description=description.strip()))

    @staticmethod
    def add_task(goal_id: int, title: str) -> None:
        """Add a trimmed task title to a goal."""
        with session_scope() as s:
            GoalRepository(s).add_task(goal_id, title.strip())

    @staticmethod
    def toggle_task(task_id: int) -> None:
        """Switch a task between complete and incomplete."""
        with session_scope() as s:
            GoalRepository(s).toggle_task(task_id)

    @staticmethod
    def delete_task(task_id: int) -> None:
        """Delete a task by its database ID."""
        with session_scope() as s:
            GoalRepository(s).delete_task(task_id)

    @staticmethod
    def delete_goal(goal_id: int) -> None:
        """Delete a goal and its tasks when the goal exists."""
        with session_scope() as s:
            repo = GoalRepository(s)
            goal = repo.get(goal_id)
            if goal:
                repo.delete(goal)

    @staticmethod
    def summary(goals: List[CareerGoal]) -> dict:
        """Summarize goal counts, task progress, and the next pending task."""
        tasks = [t for g in goals for t in g.tasks]
        done = sum(1 for t in tasks if t.done)
        pending = [t for t in tasks if not t.done]
        return {"goals": len(goals), "total": len(tasks), "done": done, "pending": len(pending),
                "progress": round(100 * done / len(tasks)) if tasks else 0,
                "next": pending[0].title if pending else None}
