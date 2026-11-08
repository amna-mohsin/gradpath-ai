"""Authentication (university-project level) + Factory pattern for creating users.

Security features
- Passwords stored as salted PBKDF2-SHA256 hashes (never plain text).
- Login throttling: 5 wrong attempts lock that email for 5 minutes.
- Same error message for "unknown email" and "wrong password" (no account enumeration).
- Officer sign-up needs a secret access code (disabled if OFFICER_ACCESS_CODE is not set).
- Demo accounts (with public passwords) are switched off when ENABLE_DEMO_LOGIN = "false".
"""
import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional

import streamlit as st

from core.config import (DEMO_OFFICER_EMAIL, DEMO_OFFICER_PASSWORD, DEMO_STUDENT_EMAIL,
                         DEMO_STUDENT_PASSWORD, officer_access_code)
from core.database import session_scope
from core.models import AuthSession, CareerOfficer, Student, User, utcnow
from core.repositories import AuthSessionRepository, UserRepository
from core.validators import check_email, check_name, check_password, check_text

ITERATIONS = 200_000
MAX_FAILS = 5
LOCK_SECONDS = 300
GENERIC_LOGIN_ERROR = "We couldn't sign you in. Check your email and password, or create an account."
SESSION_COOKIE = "gradpath_auth_session"
SESSION_DAYS = 30


def hash_password(password: str) -> str:
    """Hash a password with a fresh salt using PBKDF2-SHA256."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    """Check a password against its stored salted hash."""
    if not stored or "$" not in stored:
        return False
    salt_hex, digest_hex = stored.split("$", 1)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), ITERATIONS)
    return hmac.compare_digest(digest.hex(), digest_hex)


_DUMMY_HASH = hash_password("not-a-real-password")  # used to keep timing similar for unknown emails


@st.cache_resource(show_spinner=False)
def _attempts() -> dict:
    """In-memory failed-login counters (shared by all sessions of this server process)."""
    return {}


class UserFactory:
    """FACTORY PATTERN: callers ask for a role; the factory decides which class to build."""

    @staticmethod
    def create(role: str, email: str, name: str, password: str, **extra) -> User:
        """Build a student or officer account with normalized identity fields."""
        common = dict(email=email.strip().lower(), name=name.strip(), password_hash=hash_password(password))
        if role == "student":
            return Student(**common, university="", degree="", department="", graduation_year=2027,
                           cgpa=0.0, skills="", learning_skills="", certifications="", projects=0,
                           internships=0, work_experience_months=0, communication=0,
                           extracurricular=0, target_career="", is_demo=False, phone="", city="",
                           portfolio_url="")
        if role == "officer":
            return CareerOfficer(**common, office=extra.get("office") or "University Career Office")
        raise ValueError(f"Unknown role: {role}")


class AuthService:
    """Register users and manage authentication and persistent sessions."""

    @staticmethod
    def register(role: str, name: str, email: str, password: str, confirm: str,
                 office: str = "", access_code: str = "") -> tuple[Optional[User], str]:
        """Validate registration data and create an account when it is available."""
        for err in (check_name(name), check_email(email), check_password(password, confirm)):
            if err:
                return None, err
        if role == "officer":
            err = check_text(office, "Office / organisation name", 3, 120)
            if err:
                return None, err
            expected = officer_access_code()
            if not expected:
                return None, "Officer sign-up is switched off. The site owner must set OFFICER_ACCESS_CODE in the app secrets."
            if not hmac.compare_digest(access_code.strip(), expected):
                return None, "The officer access code is not correct. Ask your university's career office for it."
        with session_scope() as s:
            repo = UserRepository(s)
            if repo.by_email(email):
                return None, "An account with this email already exists. Try signing in."
            user = repo.add(UserFactory.create(role, email, name, password, office=office.strip()))
            return user, ""

    @staticmethod
    def lock_remaining(email: str) -> int:
        """Return the remaining login lockout duration in seconds."""
        rec = _attempts().get(email.strip().lower())
        if rec and rec["until"] > time.time():
            return int(rec["until"] - time.time()) + 1
        return 0

    @staticmethod
    def authenticate(email: str, password: str) -> Optional[User]:
        """Authenticate a user and record failures for temporary lockout."""
        key = email.strip().lower()
        wait = AuthService.lock_remaining(key)
        if wait:
            st.session_state["auth_error"] = f"Too many failed attempts. Please try again in {max(1, wait // 60 + (1 if wait % 60 else 0))} minute(s)."
            return None
        with session_scope() as s:
            user = UserRepository(s).by_email(key)
            ok = verify_password(password, user.password_hash if user else _DUMMY_HASH) and user is not None
        if ok:
            _attempts().pop(key, None)
            return user
        rec = _attempts().setdefault(key, {"fails": 0, "until": 0})
        rec["fails"] += 1
        if rec["fails"] >= MAX_FAILS:
            rec["fails"], rec["until"] = 0, time.time() + LOCK_SECONDS
        st.session_state["auth_error"] = GENERIC_LOGIN_ERROR
        return None

    @staticmethod
    def last_error() -> str:
        """Return and clear the most recent authentication error message."""
        return st.session_state.pop("auth_error", GENERIC_LOGIN_ERROR)

    @staticmethod
    def login(user: User) -> None:
        """Create a persistent browser session for the authenticated user."""
        cookie_manager = st.session_state.get("_auth_cookie_manager")
        if cookie_manager is None:
            raise RuntimeError("Persistent sign-in is unavailable because the browser cookie manager was not initialized.")
        token = secrets.token_urlsafe(32)
        expires_at = utcnow() + timedelta(days=SESSION_DAYS)
        with session_scope() as s:
            AuthSessionRepository(s).add(AuthSession(
                user_id=user.id,
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
                expires_at=expires_at,
            ))
        cookie_manager.set(SESSION_COOKIE, token,
                           expires_at=datetime.now().astimezone() + timedelta(days=SESSION_DAYS),
                           secure=True, same_site="lax")
        st.session_state["user_id"] = user.id
        st.session_state["_auth_token"] = token

    @staticmethod
    def logout() -> None:
        """Revoke the current persistent session and clear user session state."""
        cookie_manager = st.session_state.get("_auth_cookie_manager")
        token = st.session_state.get("_auth_token")
        if not token and cookie_manager is not None:
            token = cookie_manager.get(cookie=SESSION_COOKIE)
        if token:
            token_hash = hashlib.sha256(str(token).encode()).hexdigest()
            with session_scope() as s:
                auth_session = AuthSessionRepository(s).by_token_hash(token_hash)
                if auth_session:
                    s.delete(auth_session)
        if cookie_manager is not None and cookie_manager.get(cookie=SESSION_COOKIE):
            cookie_manager.delete(SESSION_COOKIE)
        for key in list(st.session_state.keys()):
            if key != "theme":
                del st.session_state[key]


@st.cache_resource(show_spinner=False)
def sync_demo_accounts(enabled: bool) -> bool:
    """Demo accounts have public passwords. Turn them off (no password) when demo login is disabled."""
    with session_scope() as s:
        repo = UserRepository(s)
        for email, pw in ((DEMO_STUDENT_EMAIL, DEMO_STUDENT_PASSWORD), (DEMO_OFFICER_EMAIL, DEMO_OFFICER_PASSWORD)):
            user = repo.by_email(email)
            if user is None:
                continue
            if enabled and not user.password_hash:
                user.password_hash = hash_password(pw)
            elif not enabled:
                user.password_hash = None
                AuthSessionRepository(s).delete_for_user(user.id)
    return True


def current_user() -> Optional[User]:
    """Resolve the current user from session state or the persistent browser token."""
    uid = st.session_state.get("user_id")
    if uid:
        with session_scope() as s:
            user = UserRepository(s).get(uid)
        if user:
            return user
        st.session_state.pop("user_id", None)

    cookie_manager = st.session_state.get("_auth_cookie_manager")
    token = cookie_manager.get(cookie=SESSION_COOKIE) if cookie_manager is not None else None
    if not token:
        return None

    token_hash = hashlib.sha256(str(token).encode()).hexdigest()
    with session_scope() as s:
        auth_session = AuthSessionRepository(s).by_token_hash(token_hash)
        if auth_session is None or auth_session.expires_at <= utcnow():
            user = None
        else:
            user = UserRepository(s).get(auth_session.user_id)
        if auth_session is not None and user is None:
            s.delete(auth_session)
    if user is None:
        cookie_manager.delete(SESSION_COOKIE)
        return None
    st.session_state["user_id"] = user.id
    st.session_state["_auth_token"] = str(token)
    return user