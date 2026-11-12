"""Student page for finding jobs, submitting applications, and tracking status."""
import streamlit as st
from services.application_service import (AVAILABILITY, ApplicationService, fit_label, status_kind)
from services.job_service import CATEGORIES, LEVELS, JobService
from services.recommendation_service import RecommendationService
from services.resume_service import ResumeService
from ui.components import badge, badges, empty_state, esc, html, insight, page_header
from views.common import fmt_time, get_student


@st.dialog("Apply for this job", width="large")
def apply_dialog(job_id: int):
    """Collect application details and submit them for an open job."""
    stu = get_student()
    job = JobService.get(job_id)
    if job is None or not job.is_open:
        st.error("This position is no longer available.")
        return
    st.markdown(f"**{job.title}** - {job.company}")
    st.caption("Your profile (CGPA, skills, readiness) is shared with the Career Office with this application. Fields marked * are required.")
    with st.form(f"apply_form_{job_id}"):
        c1, c2 = st.columns(2)
        c1.text_input("Full name", value=stu.name, disabled=True)
        c2.text_input("Email", value=stu.email, disabled=True)
        c1, c2 = st.columns(2)
        phone = c1.text_input("Phone number *", value=stu.phone or "", max_chars=20, placeholder="+923001234567", key=f"ap_phone_{job_id}")
        avail = c2.selectbox("Availability *", AVAILABILITY, index=None, placeholder="When can you start?", key=f"ap_av_{job_id}")
        portfolio = st.text_input("Portfolio / GitHub / LinkedIn (at least 1 required)", value=stu.portfolio_url or "", max_chars=200, key=f"ap_url_{job_id}")
        cover = st.text_area("Cover note * (50-1500 characters)", height=130, max_chars=1500, key=f"ap_cover_{job_id}",
                             placeholder="Tell the Career Office why you are a good fit for this role...")
        up = st.file_uploader("Resume", type=["pdf"], key=f"ap_up_{job_id}")
        consent = st.checkbox("I confirm my details are accurate and may be shared with the Career Office.", key=f"ap_ok_{job_id}")
        submitted = st.form_submit_button("Submit application", type="primary")
    if submitted:
        if up is None:
            st.error("Please upload your resume as a PDF.")
            return
        text = ResumeService.extract_text(up)
        ok, msg = ApplicationService.apply(stu, job_id, dict(phone=phone, availability=avail, portfolio_url=portfolio,
                                                             cover_note=cover, resume_text=text, resume_pdf=up.getvalue(),
                                                             consent=consent))
        if ok:
            st.session_state["apply_msg"] = msg
            st.rerun()
        else:
            st.error(msg)


def _openings(stu):
    """Render open listings ranked by the student's skill match."""
    c1, c2, c3 = st.columns([2, 1.3, 1.3])
    query = c1.text_input("Search by job title or company", placeholder="e.g. Python, analyst")
    cat = c2.selectbox("Career category", ["All"] + CATEGORIES)
    level = c3.selectbox("Experience level", ["All"] + LEVELS)
    ranked = RecommendationService.rank_jobs(stu, JobService.search(query, cat, level, only_open=True))
    if not ranked:
        empty_state("No open jobs match your search", "Try a different keyword or clear the filters.")
        return
    applied = ApplicationService.applied_job_ids(stu.id)
    st.caption(f"{len(ranked)} open listing(s), best skill match first.")
    for job, match in ranked:
        kind = "success" if match >= 70 else "info" if match >= 40 else "neutral"
        source = badge("Demo listing", "neutral") if job.is_demo else badge("Posted by Career Office", "violet")
        done = badge("Applied", "success") if job.id in applied else ""
        html(f'''<div class="gp-card"><div class="gp-row"><div><b style="font-size:1.05rem">{esc(job.title)}</b>
            <div class="gp-muted">{esc(job.company)} &middot; {esc(job.location)}</div></div>{badge(f"{match}% skill match", kind)}</div>
            <div style="margin-top:.5rem">{badge(job.category, "violet")}{badge(job.level, "info")}{source}{done}</div>
            <div style="margin-top:.4rem">{badges(job.skill_list(), "neutral")}</div></div>''')
        c1, c2, _ = st.columns([1, 1.2, 4])
        with c1:
            if job.id in applied:
                st.button("Applied", disabled=True, key=f"applied_{job.id}")
            elif st.button("Apply now", type="primary", key=f"apply_{job.id}"):
                apply_dialog(job.id)
        with c2:
            with st.popover("View details"):
                st.write(job.description)
                mine = set(stu.skill_list()) | set(stu.learning_list())
                missing = [s for s in job.skill_list() if s not in mine]
                st.write("**Skills you still need:** " + (", ".join(missing) if missing else "none - you cover all listed skills."))


@st.fragment(run_every="20s")
def _my_applications(student_id: int):
    """Render the student's latest application statuses and fit details."""
    apps = ApplicationService.for_student(student_id)
    if not apps:
        empty_state("You haven't applied yet", "Open the 'Open positions' tab and click Apply now on a job you like.")
        return
    for a in apps:
        label, kind = fit_label(a.fit_score)
        html(f'''<div class="gp-card"><div class="gp-row"><div><b>{esc(a.job.title)}</b>
            <div class="gp-muted">{esc(a.job.company)} &middot; applied {fmt_time(a.created_at)}</div></div>{badge(a.status, status_kind(a.status))}</div>
            <div style="margin-top:.4rem">{badge(label, kind)}{badge(f"Skill match {a.skill_match}%", "neutral")}{badge(f"Resume match {a.resume_match}%", "neutral")}</div></div>''')
    insight("The Career Office reviews applications from best fit to least fit. Raising your skill match (by learning the job's skills) "
            "and mentioning them in your resume improves your fit. Watch your Messages page for replies.", "How applications are ranked")


def render():
    """Render open job searches and the student's application tracker."""
    stu = get_student()
    page_header("Job opportunities", "Search listings, apply with one form, and track your applications.")
    if msg := st.session_state.pop("apply_msg", None):
        st.success(msg + " The Career Office can now see it, and you can follow its status under 'My applications'.")
    t1, t2 = st.tabs(["Open positions", "My applications"])
    with t1:
        _openings(stu)
    with t2:
        _my_applications(stu.id)
    html('<div class="gp-footer">Listings are demonstration content created for this project and are not real vacancies.</div>')
