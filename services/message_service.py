"""Direct messaging between students and career officers."""
from typing import Dict, List, Tuple

from core.database import session_scope
from core.models import Message, User
from core.repositories import MessageRepository, UserRepository
from core.validators import check_text


class MessageService:
    """Provide contacts, conversations, message delivery, and unread counts."""

    @staticmethod
    def contacts(user: User) -> Dict[int, str]:
        """List eligible contacts on the opposite side (students or officers)."""
        with session_scope() as s:
            repo = UserRepository(s)
            if user.role == "officer":
                return {st.id: f"{st.name} ({st.department or 'Student'})" for st in repo.registered_students()}
            return {o.id: f"{o.name} - {o.office}" for o in repo.officers()}

    @staticmethod
    def send(sender: User, recipient_id: int, body: str, job_id: int = None) -> Tuple[bool, str]:
        """Validate and send a message to an eligible user on the opposite side."""
        err = check_text(body, "Message", 1, 1500)
        if err:
            return False, err
        with session_scope() as s:
            recipient = UserRepository(s).get(recipient_id)
            if recipient is None or recipient.role == sender.role or recipient.id == sender.id:
                return False, "You can only message the other side (students <-> career officers)."
            MessageRepository(s).add(Message(sender_id=sender.id, recipient_id=recipient_id,
                                             body=body.strip(), job_id=job_id))
        return True, ""

    @staticmethod
    def conversations(user_id: int) -> List[dict]:
        """Return each conversation's latest message and unread-message count."""
        with session_scope() as s:
            repo, users = MessageRepository(s), UserRepository(s)
            latest: Dict[int, Message] = {}
            unread: Dict[int, int] = {}
            for m in repo.involving(user_id):
                other = m.recipient_id if m.sender_id == user_id else m.sender_id
                latest[other] = m
                if m.recipient_id == user_id and not m.is_read:
                    unread[other] = unread.get(other, 0) + 1
            out = []
            for other, m in latest.items():
                u = users.get(other)
                if u:
                    out.append({"partner_id": other, "name": u.name, "role": u.display_role(),
                                "last": m.body[:60], "time": m.created_at, "unread": unread.get(other, 0)})
            return sorted(out, key=lambda c: c["time"], reverse=True)

    @staticmethod
    def thread(user_id: int, partner_id: int) -> List[Message]:
        """Mark the pair's incoming messages read and return their thread."""
        with session_scope() as s:
            repo = MessageRepository(s)
            repo.mark_read(user_id, partner_id)
            return repo.between(user_id, partner_id)

    @staticmethod
    def unread_count(user_id: int) -> int:
        """Return the number of unread messages addressed to the user."""
        with session_scope() as s:
            return MessageRepository(s).unread_count(user_id)
