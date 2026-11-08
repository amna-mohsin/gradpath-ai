"""Student page for viewing and editing profile information."""
import streamlit as st

from core.config import CGPA_SCALE
from services.prediction_service import PredictionService
from services.student_service import ActivityService, StudentService
from ui.components import badges, esc, html, page_header, progress_bar
from ui.profile_form import profile_form
from views.common import get_student


def _summary(stu):
    """Render profile fields, confident and learning skills, and certifications."""
    items = [("Email", stu.email), ("Phone", stu.phone), ("City", stu.city), ("University", stu.university),
             ("Degree", stu.degree), ("Department", stu.department), ("Graduation year", stu.graduation_year),
             ("CGPA", f"{stu.cgpa:.2f} / {CGPA_SCALE:g}"), ("Target career", stu.target_career),
             ("Projects", stu.projects), ("Internships", stu.internships),
             ("Work experience", f"{stu.work_experience_months} months"), ("Communication", f"{stu.communication}/10"),
             ("Extracurricular", f"{stu.extracurricular}/10"), ("Portfolio", stu.portfolio_url)]
    rows = "".join(f'<div><div class="gp-muted">{k}</div><b>{esc(str(v) if v not in (None, "") else "-")}</b></div>' for k, v in items)
    html(f'<div class="gp-card"><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:1rem">{rows}</div></div>')
    html(f'<div class="gp-card"><h4>Skills I am confident in</h4>{badges(stu.skill_list(), "violet")}'
         f'<h4 style="margin-top:.8rem">Skills I am learning</h4>{badges(stu.learning_list(), "warn")}'
         f'<h4 style="margin-top:.8rem">Certifications</h4>{badges(stu.cert_list(), "info")}</div>')


def render():
    """Render the profile summary or the editable profile form."""
    stu = get_student()
    page_header("My profile", "Keep this up to date. Your readiness estimate, recommendations and job matches use it.")
    if st.session_state.pop("profile_saved", False):
        st.success("Profile saved. Your readiness estimate has been updated.")
    html(progress_bar(stu.profile_completion(), "Profile completion"))

    if not st.session_state.get("profile_edit"):
        _summary(stu)
        if st.button("Edit profile", type="primary"):
            st.session_state["profile_edit"] = True
            st.rerun()
        return

    action, record = profile_form(stu, "prof", "Save profile", show_cancel=True)
    if action == "cancel":
        st.session_state["profile_edit"] = False
        st.rerun()
    if action == "save":
        updated = StudentService.update_profile(stu.id, record)
        ActivityService.log(updated, "Profile updated", f"CGPA {updated.cgpa:.2f}, {len(updated.skill_list())} skills")
        PredictionService.estimate(updated, save=True)
        st.session_state["profile_edit"] = False
        st.session_state["profile_saved"] = True
        st.rerun()
