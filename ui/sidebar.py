"""Shared navigation sidebar for authenticated student and officer pages."""

import streamlit as st

from core.config import VERSION
from services.auth_service import AuthService
from services.message_service import MessageService
from ui.components import badge, brand, esc, html


def render_sidebar(user, pages: dict) -> None:
    """Render account details, role navigation, unread count, and sign-out control."""
    with st.sidebar:
        html(brand(34))
        kind = "violet" if user.role == "officer" else "info"
        unread = MessageService.unread_count(user.id)
        mail = badge(f"{unread} unread message{'s' if unread != 1 else ''}", "warn") if unread else ""
        html(f'''<div class="gp-card" style="margin-top:1rem;padding:.8rem 1rem">
            <div class="gp-row" style="justify-content:flex-start"><div class="gp-avatar">{esc(user.initials)}</div>
            <div><b>{esc(user.name)}</b><br>{badge(user.display_role(), kind)}</div></div>{mail}</div>''')
        for page in pages.values():
            st.page_link(page)
        st.divider()
        if st.button("Sign out", key="signout"):
            AuthService.logout()
            st.rerun()
        st.caption(f"GradPath AI v{VERSION}")
