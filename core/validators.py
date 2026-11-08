"""Input validation helpers. Each check returns an error message, or None when the value is fine."""
import re
from typing import Optional

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$")
NAME_RE = re.compile(r"^[^\W\d_]+(?:[ .'\-]+[^\W\d_]+)*\.?$")
PHONE_RE = re.compile(r"^\+?[0-9]{10,14}$")


def clean_phone(value: str) -> str:
    """Remove common visual separators before validating a phone number."""
    return re.sub(r"[\s\-().]", "", value or "")


def check_name(value: str, label: str = "Full name") -> Optional[str]:
    """Validate a human name and return a user-facing error when it is invalid."""
    v = (value or "").strip()
    if len(v) < 2:
        return f"{label} must be at least 2 characters."
    if len(v) > 80 or not NAME_RE.match(v):
        return f"{label} can only contain letters, spaces, apostrophes, dots and hyphens."
    return None


def check_email(value: str) -> Optional[str]:
    """Validate a required email address and return a readable error if needed."""
    v = (value or "").strip()
    if not v:
        return "Email address is required."
    if len(v) > 150 or not EMAIL_RE.match(v):
        return "Enter a valid email address, for example name@gmail.com."
    return None


def check_password(pw: str, confirm: Optional[str] = None) -> Optional[str]:
    """Enforce minimum password length, mixed character types, and confirmation."""
    if len(pw or "") < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        return "Password needs at least one letter and one number."
    if confirm is not None and pw != confirm:
        return "Passwords do not match."
    return None


def check_phone(value: str, required: bool = True) -> Optional[str]:
    """Validate an optional or required phone number after removing separators."""
    v = clean_phone(value)
    if not v:
        return "Phone number is required." if required else None
    if not PHONE_RE.match(v):
        return "Enter a valid phone number with 10-14 digits, e.g. +923001234567."
    return None


def check_url(value: str) -> Optional[str]:
    """Validate an optional HTTP(S) URL and return an error for malformed links."""
    v = (value or "").strip()
    if not v:
        return None
    if not re.match(r"^https?://[^\s/$.?#][^\s]*\.[^\s]{2,}$", v):
        return "Links must start with http:// or https:// (e.g. https://github.com/you)."
    return None


def check_text(value: str, label: str, min_len: int = 1, max_len: int = 200) -> Optional[str]:
    """Check trimmed text length against the caller's field-specific limits."""
    v = (value or "").strip()
    if len(v) < min_len:
        return f"{label} is required." if min_len == 1 else f"{label} must be at least {min_len} characters."
    if len(v) > max_len:
        return f"{label} must be at most {max_len} characters."
    return None
