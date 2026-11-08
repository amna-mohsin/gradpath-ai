"""Career officer page for database-backed reports and analytics."""
import pandas as pd
import streamlit as st

from services.application_service import ApplicationService
from services.job_service import JobService
from services.report_service import ReportService
from ui import charts, insights
from ui.components import empty_state, html_table, insight, metric_row, page_header
from views.common import get_officer


def render():
    """Render student readiness analytics, hiring activity, and CSV downloads."""
    get_officer()
    page_header("Reports and analytics", "All figures are calculated from records in the database.")
    snap = ReportService.snapshot(include_demo=True)
    df = snap.students
    if df.empty:
        empty_state("No records to report on", "Wait for students to complete their profiles.")
        return
    st.caption(f"Estimator: {snap.model_name}. Estimates are statistical values, not guarantees.")
    metric_row([{"label": "Records", "value": len(df)}, {"label": "Mean estimate", "value": f'{df["Estimate (%)"].mean():.0f}%'},
                {"label": "Median estimate", "value": f'{df["Estimate (%)"].median():.0f}%'},
                {"label": "Average CGPA", "value": f'{df["CGPA"].mean():.2f}'}])

    c1, c2 = st.columns(2)
    with c1:
        charts.show(charts.readiness_donut(df))
        insight(insights.readiness_donut(df))
    with c2:
        charts.show(charts.readiness_by_source(df))
        insight(insights.source(df))
    c1, c2 = st.columns(2)
    with c1:
        charts.show(charts.cgpa_hist(df))
        insight(insights.cgpa(df))
    with c2:
        charts.show(charts.department_bar(df))
        insight(insights.department(df))
    c1, c2 = st.columns(2)
    with c1:
        charts.show(charts.internship_pie(df))
        insight(insights.internship(df))
    with c2:
        if not snap.gaps.empty:
            charts.show(charts.skill_gap_bar(snap.gaps))
            insight(insights.skill_gaps(snap.gaps))

    jobs = {j.id: j for j in JobService.search()}
    counts = ApplicationService.counts()
    app_df = pd.DataFrame([{"Job": jobs[i].title, "Applications": n} for i, n in counts.items() if i in jobs])
    if not app_df.empty:
        st.markdown("##### Hiring activity")
        charts.show(charts.applications_chart(app_df))
        insight(insights.applications(app_df))

    st.markdown("##### Placement-estimate summary by department")
    summary = df.groupby("Department").agg(Students=("ID", "count"), Avg_estimate=("Estimate (%)", "mean"),
                                           Avg_CGPA=("CGPA", "mean")).round(1).reset_index()
    summary.columns = ["Department", "Students", "Average estimate (%)", "Average CGPA"]
    html_table(summary)
    d1, d2 = st.columns(2)
    d1.download_button("Download student report (CSV)", ReportService.to_csv(df.drop(columns=["ID"])), "gradpath_report.csv", "text/csv")
    d2.download_button("Download skill-gap report (CSV)", ReportService.to_csv(snap.gaps), "gradpath_skill_gaps.csv", "text/csv")
