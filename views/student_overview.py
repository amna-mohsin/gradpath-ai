"""Student dashboard with readiness, goals, opportunities, and recent activity."""
import streamlit as st

from data.career_requirements import SKILL_CATEGORY
from services.application_service import ApplicationService, fit_label, status_kind
from services.goal_service import GoalService
from services.message_service import MessageService
from services.job_service import JobService
from services.prediction_service import PredictionService
from services.recommendation_service import RecommendationService
from services.skill_gap_service import SkillGapService
from services.student_service import ActivityService
from ui.components import (badge, badges, category_kind, esc, go, html, list_items, metric_row,
                           page_header, progress_bar)
from views.common import fmt_time, get_student


def render():
    """Render the student's profile summary, recommendations, and dashboard links."""
    stu = get_student()
    res = PredictionService.estimate(stu, save=stu.profile_completion() >= 50)
    if st.session_state.pop("welcome", False):
        st.success("Your profile is set up. This is your dashboard: your estimate, skills, jobs and next steps are all here.")
    page_header(f"Welcome back, {stu.first_name}!", "Small steps today can open bigger opportunities tomorrow.")
    unread = MessageService.unread_count(stu.id)
    if unread:
        st.info(f"You have {unread} unread message{'s' if unread != 1 else ''} from the Career Office.")
        go("messages", "Open messages", primary=True, widget_key="ov_msgs")

    c1, c2 = st.columns([3, 1], vertical_alignment="center")
    with c1:
        html(progress_bar(stu.profile_completion(), "Profile completion"))
    with c2:
        go("profile", "Update profile", widget_key="ov_profile")

    metric_row([
        {"label": "CGPA", "value": f"{stu.cgpa or 0:.2f}", "hint": "Out of 4.0"},
        {"label": "Projects completed", "value": stu.projects or 0},
        {"label": "Internship experience", "value": stu.internships or 0, "hint": "Internships"},
        {"label": "Career-readiness score", "value": f"{res.probability:.0f}%", "hint": "Demo estimate"},
    ])

    left, right = st.columns([3, 2], gap="large")
    with left:
        html(f'''<div class="gp-accent"><div style="opacity:.85;font-weight:600">Placement readiness</div>
            <div class="big">{res.probability:.0f}%</div><div style="margin-top:.5rem"><b>{esc(res.category)}</b></div>
            <p>Based on {esc(res.strategy.lower())}. {len(res.strengths)} strong factor(s) and {len(res.weaknesses)} area(s) to improve.</p></div>''')
        go("readiness", "View full analysis", primary=True, widget_key="ov_readiness")

        st.markdown("##### Skills overview")
        confident = set(stu.skill_list())
        cats = [(c, len(confident & set(s)), len(s)) for c, s in SKILL_CATEGORY.items()]
        strong = [c for c in sorted(cats, key=lambda x: -x[1]) if c[1] > 0][:3]
        goal_sum = GoalService.summary(stu.goals)
        gap = SkillGapService.analyze(stu, stu.target_career or "Software Developer")
        body = f'<p><b>Current skills</b></p>{badges(stu.skill_list(), "violet")}'
        body += "<p style='margin-top:.6rem'><b>Strongest categories</b></p>"
        body += "".join(progress_bar(100 * n / t, name, green=True) for name, n, t in strong) or '<span class="gp-muted">Add skills in your profile.</span>'
        body += "<p style='margin-top:.6rem'><b>Skills to improve</b></p>" + badges([r["skill"] for r in gap["priorities"]] or stu.learning_list(), "warn")
        body += "<p style='margin-top:.6rem'><b>Progress toward career goals</b></p>" + progress_bar(goal_sum["progress"], f'{goal_sum["done"]}/{goal_sum["total"]} tasks done')
        html(f'<div class="gp-card">{body}</div>')

        st.markdown("##### Recommended actions")
        actions = RecommendationService.next_actions(res)
        if actions:
            html('<div class="gp-card">' + list_items([f'<b>{i}. {esc(a["title"])}</b><br><span class="gp-muted">{esc(a["detail"])}</span>' for i, a in enumerate(actions, 1)]) + '</div>')
        else:
            html('<div class="gp-card">You are in a strong position. Keep your goals and projects up to date.</div>')

    with right:
        st.markdown("##### Recommended opportunities")
        st.caption("Fictional demo listings.")
        ranked = RecommendationService.rank_jobs(stu, JobService.search())[:3]
        for job, match in ranked:
            kind = "success" if match >= 70 else "info" if match >= 40 else "neutral"
            html(f'''<div class="gp-card"><div class="gp-row"><b>{esc(job.title)}</b>{badge(f"{match}% match", kind)}</div>
                <p>{esc(job.company)} &middot; {esc(job.level)}</p>{badges(job.skill_list()[:4], "neutral")}</div>''')
        go("jobs", "Browse all jobs", widget_key="ov_jobs")

        apps = ApplicationService.for_student(stu.id)[:3]
        if apps:
            st.markdown("##### My applications")
            for a in apps:
                html(f'<div class="gp-card" style="padding:.7rem 1rem"><div class="gp-row"><b>{esc(a.job.title)}</b>{badge(a.status, status_kind(a.status))}</div>'
                     f'<span class="gp-muted">{esc(a.job.company)}</span></div>')
            go("jobs", "Track applications", widget_key="ov_apps")

        st.markdown("##### Recent activity")
        acts = ActivityService.recent(stu.id, 5)
        if acts:
            html('<div class="gp-card">' + list_items([f'<b>{esc(a.action)}</b> <span class="gp-muted">{esc(a.detail)} &middot; {fmt_time(a.created_at)}</span>' for a in acts]) + '</div>')
        else:
            html('<div class="gp-card gp-muted">No activity yet. Update your profile to get started.</div>')
