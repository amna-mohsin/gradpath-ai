"""Student page for keyword-based resume analysis."""
import streamlit as st

from data.career_requirements import CAREERS
from services.resume_service import ResumeService
from services.student_service import ActivityService
from ui.components import badges, esc, html, list_items, metric_row, page_header, progress_bar
from views.common import get_student


def render():
    """Render resume upload, career selection, and analysis results."""
    stu = get_student()
    page_header("Make your resume stronger", "Upload your resume as a PDF and compare it with a target career.")
    careers = list(CAREERS)
    career = st.selectbox("Target career", careers, index=careers.index(stu.target_career) if stu.target_career in careers else 0)
    up = st.file_uploader("Upload resume", type=["pdf"])
    if st.button("Analyze resume", type="primary"):
        if up is None:
            st.error("Please upload your resume as a PDF.")
            return
        content = ResumeService.extract_text(up)
        if len(content.split()) < 40:
            st.error("Please upload a readable PDF containing at least 40 words.")
        else:
            st.session_state["resume_result"] = (career, ResumeService.analyze(content, career))
            ActivityService.log(stu, "Resume analysed", career)

    if "resume_result" not in st.session_state:
        return
    used_career, r = st.session_state["resume_result"]
    st.divider()
    st.markdown(f"#### Results for {used_career}")
    metric_row([{"label": "Keyword-match score", "value": f'{r["score"]}/100'},
                {"label": "Required skills found", "value": f'{len(r["matched"])}/{len(r["matched"]) + len(r["missing"])}'},
                {"label": "Words", "value": r["words"]}])
    html(f'<div class="gp-card">{progress_bar(r["score"], "Overall score", green=r["score"] >= 70)}</div>')
    c1, c2 = st.columns(2)
    with c1:
        html(f'<div class="gp-card"><h4>Recognised skill keywords</h4>{badges(r["found"], "success")}</div>')
    with c2:
        html(f'<div class="gp-card"><h4>Missing relevant keywords</h4>{badges(r["missing"], "warn")}</div>')
    html('<div class="gp-card"><h4>Structure checks</h4>' + list_items([("Pass: " if ok else "Fix: ") + esc(l) for l, ok in r["checks"]]) + "</div>")
    html('<div class="gp-card"><h4>Suggested improvements</h4>' + (list_items([esc(t) for t in r["tips"]]) if r["tips"] else "<p>Nothing major to fix.</p>") + "</div>")
    html('<div class="gp-card"><h4>Project or experience ideas</h4>' + list_items([esc(p) for p in r["project_ideas"]]) + "</div>")
