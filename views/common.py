"""Shared authentication and formatting helpers for Streamlit pages."""
import streamlit as st

from core.models import CareerOfficer, Student
from services.auth_service import current_user



def get_student() -> Student:
    """Return the signed-in student or stop rendering with an access error."""
    user = current_user()
    if not isinstance(user, Student):
        st.error("This page is for student accounts.")
        st.stop()
    return user


def get_officer() -> CareerOfficer:
    """Return the signed-in officer or stop rendering with an access error."""
    user = current_user()
    if not isinstance(user, CareerOfficer):
        st.error("This page is for career officer accounts.")
        st.stop()
    return user


def fmt_time(dt) -> str:
    """Format a timestamp for compact page display."""
    return dt.strftime("%d %b, %H:%M") if dt else ""


def get_user():
    """Return the signed-in user or stop rendering when no user is present."""
    user = current_user()
    if user is None:
        st.stop()
    return user
