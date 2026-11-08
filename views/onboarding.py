"""Student setup page for completing a profile after registration."""
import streamlit as st

from services.auth_service import AuthService
from services.prediction_service import PredictionService
from services.student_service import ActivityService, StudentService
from ui.components import esc, html, page_header
from ui.profile_form import profile_form
from views.common import get_student


def render():
    """Render profile onboarding and save the first readiness estimate."""
    stu = get_student()
    html(f'''<div class="gp-hero" style="padding:1.6rem 1.8rem"><span class="gp-badge b-violet">Step 1 of 1 - set up your profile</span>
        <h1 style="font-size:2.1rem">Welcome, {esc(stu.first_name)}! Let's build your profile.</h1>
        <p>It takes about two minutes. Your answers power your readiness estimate, skill-gap analysis and job matches,
        so honest details give you better guidance. Fields marked * are required.</p></div>''')
    action, record = profile_form(stu, "onb", "Finish and go to my dashboard")
    if action == "save":
        updated = StudentService.update_profile(stu.id, record)
        ActivityService.log(updated, "Profile created")
        PredictionService.estimate(updated, save=True)
        st.session_state["welcome"] = True
        st.rerun()
    st.divider()
    if st.button("Sign out", key="onb_signout"):
        AuthService.logout()
        st.rerun()
