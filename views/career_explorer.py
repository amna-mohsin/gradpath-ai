"""Student pages for browsing career paths and preparation guidance."""
import streamlit as st

from data.career_requirements import CAREERS
from services.skill_gap_service import SkillGapService
from ui.components import badge, badges, esc, html, list_items, page_header, progress_bar, status_kind
from views.common import get_student


@st.dialog("Career details", width="large")
def career_dialog(name: str):
    """Show career responsibilities, skill match, and preparation suggestions."""
    stu = get_student()
    c = CAREERS[name]
    g = SkillGapService.analyze(stu, name)
    st.markdown(f"### {name}")
    st.write(c["description"])
    html(f'<div class="gp-card">{progress_bar(g["match"], "Your current skill match", green=g["match"] >= 70)}</div>')
    c1, c2 = st.columns(2)
    with c1:
        html('<div class="gp-card"><h4>Typical responsibilities</h4>' + list_items([esc(r) for r in c["responsibilities"]]) + "</div>")
        html('<div class="gp-card"><h4>Skills employers look for</h4>' + "".join(
            badge(r["skill"], status_kind(r["status"])) for r in g["rows"]) +
            '<p style="margin-top:.5rem">Green = you have it, amber = still learning, red = missing.</p></div>')
    with c2:
        html('<div class="gp-card"><h4>Recommended preparation</h4>' + list_items([esc(p) for p in c["preparation"]]) + "</div>")
        html('<div class="gp-card"><h4>Portfolio project ideas</h4>' + list_items([esc(p) for p in c["projects"]]) + "</div>")
    if st.button("Open full skill-gap analysis", type="primary", key=f"dlg_gap_{name}"):
        st.session_state["pref_career"] = name
        st.switch_page(st.session_state["nav"]["skill-gap"])


def render():
    """Render career choices and open the selected career detail dialog."""
    get_student()
    page_header("Career explorer", "Explore career paths and what it takes to prepare for them. Click Explore for details.")
    names = list(CAREERS)
    for i in range(0, len(names), 2):
        for col, name in zip(st.columns(2, gap="large"), names[i:i + 2]):
            c = CAREERS[name]
            with col:
                html(f'''<div class="gp-card"><h4>{esc(name)}</h4><p>{esc(c["description"])}</p>
                    <p style="margin-top:.6rem"><b>Relevant skills</b></p>{badges(list(c["skills"])[:7], "violet")}</div>''')
                if st.button(f"Explore {name}", key=f"explore_{name}", type="primary"):
                    career_dialog(name)
