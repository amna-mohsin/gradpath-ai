"""Career officer page for viewing and editing account profile details."""
import streamlit as st

from services.officer_service import OfficerService
from ui.components import esc, html, page_header
from views.common import get_officer


def render():
    """Render the officer profile summary and its edit form."""
    officer = get_officer()
    page_header("My profile", "Manage your name and company or Career Office details.")
    if st.session_state.pop("officer_profile_saved", False):
        st.success("Profile saved.")

    html(f'''<div class="gp-card"><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1rem">
        <div><div class="gp-muted">Name</div><b>{esc(officer.name)}</b></div>
        <div><div class="gp-muted">Email</div><b>{esc(officer.email)}</b></div>
        <div><div class="gp-muted">Company / office</div><b>{esc(officer.office)}</b></div>
        </div></div>''')

    if not st.session_state.get("officer_profile_edit"):
        if st.button("Edit profile", type="primary"):
            st.session_state["officer_profile_edit"] = True
            st.rerun()
        return

    with st.form("officer_profile_form"):
        name = st.text_input("Full name *", value=officer.name, max_chars=80)
        st.text_input("Email", value=officer.email, disabled=True)
        office = st.text_input("Company / office name *", value=officer.office, max_chars=120)
        save, cancel = st.columns(2)
        submitted = save.form_submit_button("Save profile", type="primary")
        cancelled = cancel.form_submit_button("Cancel changes")

    if cancelled:
        st.session_state["officer_profile_edit"] = False
        st.rerun()
    if submitted:
        _, error = OfficerService.update_profile(officer.id, name, office)
        if error:
            st.error(error)
            return
        st.session_state["officer_profile_edit"] = False
        st.session_state["officer_profile_saved"] = True
        st.rerun()
