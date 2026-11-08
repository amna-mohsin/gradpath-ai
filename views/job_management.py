"""Career officer page for creating and managing job listings."""
import streamlit as st

from data.career_requirements import SKILL_CATALOG
from services.application_service import ApplicationService
from services.job_service import CATEGORIES, LEVELS, JobService
from services.student_service import ActivityService
from ui.components import badge, badges, confirm_box, empty_state, esc, html, page_header, request_confirm
from views.common import get_officer


def _form(prefix: str, job=None):
    """Render listing fields and return their normalized form values."""
    c1, c2 = st.columns(2)
    title = c1.text_input("Job title *", value=job.title if job else "", key=f"{prefix}_t", max_chars=140)
    company = c2.text_input("Company *", value=job.company if job else "", key=f"{prefix}_c", max_chars=140)
    c1, c2, c3 = st.columns(3)
    cat = c1.selectbox("Career category", CATEGORIES, index=CATEGORIES.index(job.category) if job and job.category in CATEGORIES else 0, key=f"{prefix}_cat")
    level = c2.selectbox("Experience level", LEVELS, index=LEVELS.index(job.level) if job and job.level in LEVELS else 0, key=f"{prefix}_l")
    loc = c3.text_input("Location", value=job.location if job else "Remote", key=f"{prefix}_loc", max_chars=120)
    skills = st.multiselect("Required skills *", SKILL_CATALOG, default=[s for s in job.skill_list() if s in SKILL_CATALOG] if job else [], key=f"{prefix}_s")
    desc = st.text_area("Description * (at least 20 characters)", value=job.description if job else "", key=f"{prefix}_d", height=100, max_chars=2000)
    return dict(title=title.strip(), company=company.strip(), category=cat, level=level, location=loc.strip(), skills=skills, description=desc.strip())


def _save_data(d):
    """Convert selected skill names to the listing's stored string format."""
    return {**d, "skills": ",".join(d["skills"])}


def render():
    """Render listing search, creation, editing, and management controls."""
    officer = get_officer()
    page_header("Job management", "Add, edit, close and remove listings. Open jobs appear instantly for every student.")
    if msg := st.session_state.pop("job_msg", None):
        st.success(msg)
    tab_list, tab_add = st.tabs(["All listings", "Add listing"])

    with tab_add:
        with st.form("add_job"):
            d = _form("add")
            if st.form_submit_button("Add listing", type="primary"):
                err = JobService.validate(d["title"], d["company"], d["category"], d["level"], d["skills"], d["description"])
                if err:
                    st.error(err)
                else:
                    JobService.create(_save_data(d), officer.id)
                    ActivityService.log(officer, "Job added", d["title"])
                    st.session_state["job_msg"] = f'Added "{d["title"]}". Students can see and apply to it now.'
                    st.rerun()

    with tab_list:
        c1, c2, c3 = st.columns([2, 1.3, 1.3])
        q = c1.text_input("Search listings")
        cat = c2.selectbox("Category", ["All"] + CATEGORIES, key="jm_cat")
        lvl = c3.selectbox("Level", ["All"] + LEVELS, key="jm_lvl")
        jobs = JobService.search(q, cat, lvl)
        counts = ApplicationService.counts()
        st.caption(f"{len(jobs)} listing(s)")
        if not jobs:
            empty_state("No listings found", "Adjust your filters or add a new listing.")
        for job in jobs:
            tag = badge("Demo seed", "neutral") if job.is_demo else badge("Added by office", "violet")
            state = badge("Open", "success") if job.is_open else badge("Closed", "danger")
            n = counts.get(job.id, 0)
            html(f'<div class="gp-card"><div class="gp-row"><b>{esc(job.title)}</b><div>{state}{tag}</div></div><p>{esc(job.company)} &middot; {esc(job.level)} &middot; {esc(job.category)} &middot; {n} applicant(s)</p>{badges(job.skill_list())}</div>')
            if job.is_demo or job.created_by != officer.id:
                continue
            with st.expander("Edit, close or delete"):
                with st.form(f"edit_{job.id}"):
                    d = _form(f"e{job.id}", job)
                    if st.form_submit_button("Save changes", type="primary"):
                        err = JobService.validate(d["title"], d["company"], d["category"], d["level"], d["skills"], d["description"])
                        if err:
                            st.error(err)
                        else:
                            if JobService.update(job.id, _save_data(d), officer.id):
                                ActivityService.log(officer, "Job edited", d["title"])
                                st.session_state["job_msg"] = f'Updated "{d["title"]}".'
                                st.rerun()
                            else:
                                st.error("You can only edit listings created by your account.")
                c1, c2, _ = st.columns([1.4, 1.4, 3])
                if c1.button("Close listing" if job.is_open else "Reopen listing", key=f"jo_{job.id}"):
                    if JobService.set_open(job.id, not job.is_open, officer.id):
                        st.session_state["job_msg"] = f'"{job.title}" is now {"closed" if job.is_open else "open"}.'
                        st.rerun()
                    else:
                        st.error("You can only change listings created by your account.")
                if c2.button("Delete listing", key=f"jd_{job.id}"):
                    request_confirm(f"job_{job.id}")
                    st.rerun()
                confirm_box(f"job_{job.id}", f'Delete "{job.title}"? Its {n} application(s) will be deleted too. This cannot be undone.',
                            lambda jid=job.id, t=job.title: _delete_listing(jid, t, officer))


def _delete_listing(job_id: int, title: str, officer) -> None:
    """Delete an officer-owned listing and record its activity."""
    if not JobService.delete(job_id, officer.id):
        st.error("You can only delete listings created by your account.")
        return
    ActivityService.log(officer, "Job deleted", title)
    st.session_state["job_msg"] = f'Deleted "{title}".'
