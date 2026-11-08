"""Career officer page for reviewing and managing job applications."""
import pandas as pd
import streamlit as st

from services.application_service import STATUSES, W_READY, W_RESUME, W_SKILL, ApplicationService, fit_label, status_kind
from services.job_service import JobService
from services.report_service import ReportService
from ui.components import (badge, badges, category_kind, empty_state, esc, html, insight, metric_row, page_header)
from views.common import fmt_time, get_officer


def render():
    """Render ranked applications and the officer's review controls."""
    get_officer()
    page_header("Applications", "Review applicants for each job, ranked from best fit to least fit.")
    jobs = JobService.search()
    if not jobs:
        empty_state("No jobs yet", "Add a job in Job Management first.")
        return
    counts = ApplicationService.counts()
    ids = [j.id for j in jobs]
    by_id = {j.id: j for j in jobs}
    job_id = st.selectbox("Job", ids, format_func=lambda i: f"{by_id[i].title} - {by_id[i].company}  ({counts.get(i, 0)} applicant(s))")
    apps = ApplicationService.for_job(job_id)
    insight(f"Fit score (0-100) = <b>{int(W_SKILL * 100)}%</b> match between the job's skills and the student's profile + "
            f"<b>{int(W_RESUME * 100)}%</b> job keywords found in their resume + <b>{int(W_READY * 100)}%</b> placement readiness. "
            "It is a screening aid to help you prioritise, not a hiring decision. Always review the full application.", "How the ranking works")
    if not apps:
        empty_state("No applications yet", "When students apply to this job they will appear here, best fit first.")
        return

    metric_row([{"label": "Applicants", "value": len(apps)},
                {"label": "Strong fits", "value": sum(1 for a in apps if a.fit_score >= 75)},
                {"label": "Shortlisted or later", "value": sum(1 for a in apps if a.status in ("Shortlisted", "Interview", "Offer"))}])
    table = pd.DataFrame([{"Rank": i, "Candidate": a.student.name, "Fit score": a.fit_score, "Fit": fit_label(a.fit_score)[0],
                           "Skill match %": a.skill_match, "Resume match %": a.resume_match,
                           "Readiness": a.readiness_category, "Status": a.status,
                           "Source": "Demo (fictional)" if a.student.is_demo else "Registered"} for i, a in enumerate(apps, 1)])
    st.download_button("Download ranked list (CSV)", ReportService.to_csv(table), f"applicants_job_{job_id}.csv", "text/csv")

    for rank, a in enumerate(apps, 1):
        label, kind = fit_label(a.fit_score)
        s = a.student
        demo = badge("Demo record", "neutral") if s.is_demo else ""
        html(f'''<div class="gp-card"><div class="gp-row"><div><b>#{rank} &nbsp;{esc(s.name)}</b>
            <div class="gp-muted">{esc(s.department)} &middot; CGPA {s.cgpa:.2f} &middot; applied {fmt_time(a.created_at)}</div></div>
            <div style="text-align:right"><b style="font-size:1.4rem">{a.fit_score}</b><span class="gp-muted">/100</span></div></div>
            <div style="margin-top:.4rem">{badge(label, kind)}{badge(a.status, status_kind(a.status))}
            {badge(a.readiness_category, category_kind(a.readiness_category))}{badge(f"Skills {a.skill_match}%", "neutral")}
            {badge(f"Resume {a.resume_match}%", "neutral")}{demo}</div></div>''')
        with st.expander(f"Review {s.name}"):
            c1, c2 = st.columns(2)
            c1.markdown(f"**Email:** {s.email}  \n**Phone:** {a.phone or '-'}  \n**City:** {s.city or '-'}  \n**Availability:** {a.availability}")
            c2.markdown(f"**University:** {s.university}  \n**Target career:** {s.target_career or '-'}  \n**Portfolio:** {a.portfolio_url or '-'}")
            html(f'<p><b>Skills</b></p>{badges(s.skill_list(), "violet")}<p><b>Still learning</b></p>{badges(s.learning_list(), "warn")}')
            st.markdown("**Cover note**")
            st.write(a.cover_note)
            st.markdown("**Resume PDF**")
            if a.resume_pdf:
                st.pdf(a.resume_pdf)
                st.download_button("Download resume PDF", a.resume_pdf, f"{s.name.replace(' ', '_')}_resume.pdf",
                                   "application/pdf", key=f"resume_pdf_{a.id}")
            else:
                st.caption("A PDF file is not available for this application.")
            c1, c2, c3 = st.columns([2, 1, 1.4], vertical_alignment="bottom")
            new = c1.selectbox("Update status", STATUSES, index=STATUSES.index(a.status) if a.status in STATUSES else 0, key=f"st_{a.id}")
            if c2.button("Save status", key=f"sv_{a.id}", type="primary"):
                ApplicationService.update_status(a.id, new)
                st.rerun()
            if s.is_demo and s.password_hash is None:
                c3.caption("Demo record: cannot receive messages.")
            elif c3.button("Message candidate", key=f"msg_{a.id}"):
                st.session_state["msg_partner"] = s.id
                st.switch_page(st.session_state["nav"]["messages"])
