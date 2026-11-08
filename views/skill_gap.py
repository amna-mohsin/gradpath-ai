"""Student page comparing skills with career-path requirements."""
import streamlit as st

from data.career_requirements import CAREERS
from services.skill_gap_service import SkillGapService
from ui.components import badge, esc, html, insight, list_items, metric_row, page_header, progress_bar, status_kind
from views.common import get_student

IMPORTANCE = {3: "High", 2: "Medium", 1: "Low"}


def render():
    """Render the selected career's skill match, gaps, and learning priorities."""
    stu = get_student()
    page_header("Skill-gap analysis", "Compare your skills with an example career path and see what to learn next.")
    careers = list(CAREERS)
    default = st.session_state.get("pref_career") or stu.target_career
    career = st.selectbox("Choose a career path", careers, index=careers.index(default) if default in careers else 0, key="gap_select")
    st.caption("Requirements are illustrative examples, not verified requirements from all employers.")
    g = SkillGapService.analyze(stu, career)

    metric_row([
        {"label": "Skill match", "value": f'{g["match"]}%'},
        {"label": "Skills available", "value": g["counts"]["Available"]},
        {"label": "Needs improvement", "value": g["counts"]["Needs improvement"]},
        {"label": "Missing", "value": g["counts"]["Missing"]},
    ])
    html(f'<div class="gp-card">{progress_bar(g["match"], f"Match with {career}", green=g["match"] >= 70)}</div>')
    insight(f"Your skill match is <b>{g['match']}%</b>. Skills you have count fully, skills you are still learning count half, and missing skills count zero; "
            "more important skills weigh more. Close the high-importance gaps first for the biggest jump.")

    rows = "".join(f'<tr><td><b>{esc(r["skill"])}</b></td><td>{badge(r["status"], status_kind(r["status"]))}</td>'
                   f'<td>{IMPORTANCE[r["importance"]]}</td><td>{esc(r["recommendation"])}</td></tr>' for r in g["rows"])
    html(f'<div class="gp-card" style="overflow-x:auto"><table class="gp-table"><tr><th>Skill</th><th>Current status</th><th>Importance</th><th>Recommendation</th></tr>{rows}</table></div>')

    c1, c2 = st.columns(2)
    with c1:
        items = [f'<b>{esc(r["skill"])}</b> <span class="gp-muted">({r["status"].lower()}, {IMPORTANCE[r["importance"]].lower()} importance)</span>' for r in g["priorities"]]
        html('<div class="gp-card"><h4>Learning priorities</h4>' + (list_items(items) if items else "<p>You cover every listed skill. Deepen them with projects.</p>") + "</div>")
    with c2:
        html('<div class="gp-card"><h4>Suggested portfolio projects</h4>' + list_items([esc(p) for p in g["projects"]]) + "</div>")
