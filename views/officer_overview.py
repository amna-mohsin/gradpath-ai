"""Career officer dashboard with student, job, and application summaries."""
import streamlit as st

from services.application_service import ApplicationService
from services.job_service import JobService
from services.message_service import MessageService
from services.report_service import ReportService
from services.student_service import ActivityService
from ui import charts, insights
from ui.components import badge, category_kind, empty_state, esc, go, html, insight, list_items, metric_row, page_header
from views.common import fmt_time, get_officer


def render():
    """Render office-wide readiness metrics, charts, activity, and quick links."""
    officer = get_officer()
    page_header("Career office overview", "Employability snapshot calculated from the student records in the database.")
    snap = ReportService.snapshot(include_demo=True)
    df = snap.students
    jobs = JobService.search()
    apps = ApplicationService.all_applications()
    unread = MessageService.unread_count(officer.id)
    if df.empty:
        empty_state("No student records yet", "Records appear here once students complete their profiles or demo data is seeded.")
        return
    demo_n = int((df["Source"] != "Registered").sum())
    st.caption(f"{len(df)} records ({demo_n} fictional demo, {len(df) - demo_n} registered). Estimator: {snap.model_name}.")
    ready = int((df["Readiness"] == "Job Ready").sum())
    metric_row([
        {"label": "Total student records", "value": len(df)},
        {"label": "Average CGPA", "value": f'{df["CGPA"].mean():.2f}'},
        {"label": "Job Ready students", "value": ready, "hint": f"{100 * ready / len(df):.0f}% of records"},
        {"label": "With internship experience", "value": int((df["Internships"] > 0).sum())},
    ])
    metric_row([
        {"label": "Open jobs", "value": sum(1 for j in jobs if j.is_open), "hint": f"{len(jobs)} listings in total"},
        {"label": "Applications received", "value": len(apps), "hint": f"{sum(1 for a in apps if a.status == 'Submitted')} awaiting review"},
        {"label": "Unread messages", "value": unread},
    ])
    counts = df["Readiness"].value_counts()
    html("".join(badge(f"{k}: {counts.get(k, 0)}", category_kind(k)) for k in ["Needs Improvement", "Developing", "Job Ready"]))

    c1, c2 = st.columns(2)
    with c1:
        charts.show(charts.readiness_donut(df))
        insight(insights.readiness_donut(df))
    with c2:
        charts.show(charts.department_bar(df))
        insight(insights.department(df))

    c1, c2 = st.columns([2, 1], gap="large")
    with c1:
        st.markdown("##### Recently created profiles")
        acts = ActivityService.recent_profiles(6)
        if acts:
            html('<div class="gp-card">' + list_items([f'<b>{esc(a.actor_name)}</b> created a profile '
                                                       f'<span class="gp-muted">&middot; {fmt_time(a.created_at)}</span>'
                                                       for a in acts]) + "</div>")
        else:
            st.caption("No new profiles yet.")
    with c2:
        st.markdown("##### Quick links")
        go("applications", "Review applications", primary=True, widget_key="of_apps")
        go("job-management", "Manage job listings", widget_key="of_jobs")
        go("messages", "Open messages", widget_key="of_msg")
