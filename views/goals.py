"""Student page for creating career goals and tracking their tasks."""
import streamlit as st

from services.goal_service import GoalService
from services.student_service import ActivityService
from ui.components import confirm_box, empty_state, esc, html, metric_row, page_header, progress_bar, request_confirm
from views.common import get_student


def _toggle(task_id):
    """Toggle a task's completion state after its checkbox changes."""
    GoalService.toggle_task(task_id)


def render():
    """Render goal summaries, goal editing forms, and task lists."""
    stu = get_student()
    page_header("Career goals and progress", "Break big ambitions into small tasks and watch your progress grow.")
    goals = GoalService.list_goals(stu.id)
    s = GoalService.summary(goals)
    metric_row([{"label": "Goals", "value": s["goals"]}, {"label": "Completed tasks", "value": s["done"]},
                {"label": "Pending tasks", "value": s["pending"]}, {"label": "Overall progress", "value": f'{s["progress"]}%'}])
    html(f'<div class="gp-card">{progress_bar(s["progress"], "Overall completion", green=True)}'
         f'<p style="margin-top:.5rem"><b>Suggested next action:</b> {esc(s["next"] or "Create a goal and add your first task.")}</p></div>')

    with st.expander("Create a new goal", expanded=not goals):
        with st.form("new_goal", clear_on_submit=True):
            title = st.text_input("Goal title", max_chars=160, placeholder="e.g. Build a portfolio project")
            desc = st.text_area("Description (optional)", height=80, max_chars=400)
            if st.form_submit_button("Create goal", type="primary"):
                if len(title.strip()) >= 3:
                    GoalService.create_goal(stu.id, title, desc)
                    ActivityService.log(stu, "Goal created", title)
                    st.rerun()
                else:
                    st.error("Please enter a goal title (at least 3 characters).")

    t_goals, t_pending, t_done = st.tabs(["My goals", "Pending tasks", "Completed tasks"])
    with t_goals:
        if not goals:
            empty_state("No goals yet", "Create your first goal above, then add small tasks to it.")
        for g in goals:
            with st.container(border=True):
                st.markdown(f"**{g.title}**")
                if g.description:
                    st.caption(g.description)
                html(progress_bar(g.progress, f"{sum(t.done for t in g.tasks)}/{len(g.tasks)} tasks"))
                for t in g.tasks:
                    c1, c2 = st.columns([8, 1.3])
                    c1.checkbox(t.title, value=t.done, key=f"task_{t.id}", on_change=_toggle, args=(t.id,))
                    if c2.button("Delete", key=f"deltask_{t.id}"):
                        request_confirm(f"task_{t.id}")
                        st.rerun()
                    confirm_box(f"task_{t.id}", f'Delete the task "{t.title}"?', lambda tid=t.id: GoalService.delete_task(tid))
                with st.form(f"addtask_{g.id}", clear_on_submit=True):
                    c1, c2 = st.columns([5, 1.2], vertical_alignment="bottom")
                    new = c1.text_input("Add a task", key=f"newtask_{g.id}", label_visibility="collapsed",
                                        placeholder="Add a task...", max_chars=200)
                    if c2.form_submit_button("Add task") and new.strip():
                        GoalService.add_task(g.id, new)
                        st.rerun()
                confirm_box(f"goal_{g.id}", f'Delete the goal "{g.title}" and all its tasks?', lambda gid=g.id: GoalService.delete_goal(gid))
                if not st.session_state.get(f"confirm_goal_{g.id}"):
                    if st.button("Delete goal", key=f"delgoal_{g.id}"):
                        request_confirm(f"goal_{g.id}")
                        st.rerun()
    for tab, done, msg in ((t_pending, False, "Nothing pending. Add tasks to your goals."), (t_done, True, "Completed tasks will show up here.")):
        with tab:
            items = [(g, t) for g in goals for t in g.tasks if t.done == done]
            if not items:
                empty_state("Nothing here yet", msg)
            for g, t in items:
                html(f'<div class="gp-card" style="padding:.7rem 1rem"><b>{esc(t.title)}</b> <span class="gp-muted">- {esc(g.title)}</span></div>')
