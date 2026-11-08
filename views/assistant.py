"""Student-facing career assistant chat page."""
import streamlit as st

from services.chatbot_service import ChatbotFactory
from services.prediction_service import PredictionService
from ui.components import badge, html, page_header
from views.common import get_student

QUICK = ["How can I improve my career readiness?", "Which skills should I learn?", "How do I analyze my resume?",
         "Where can I find job opportunities?", "How do I track my career goals?"]


def render():
    """Render chat history, suggested prompts, and assistant responses."""
    stu = get_student()
    bot = ChatbotFactory.create()
    page_header("Career assistant", "Ask about readiness, skills, resumes, jobs and goals.")
    html(badge(bot.label, "violet" if "AI" in bot.label else "neutral") +
         (badge("Demo assistant - rule-based answers", "neutral") if "Rule" in bot.label else ""))
    msgs = st.session_state.setdefault("chat", [{"role": "assistant", "content": f"Hi {stu.first_name}! What would you like help with today?"}])

    cols = st.columns(len(QUICK))
    picked = None
    for i, (c, q) in enumerate(zip(cols, QUICK)):
        if c.button(q, key=f"q{i}"):
            picked = q
    for m in msgs:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    prompt = st.chat_input("Ask a career question...") or picked
    if prompt:
        msgs.append({"role": "user", "content": prompt})
        res = PredictionService.estimate(stu)
        ctx = (f"Target career {stu.target_career or 'unset'}; CGPA {stu.cgpa}; projects {stu.projects}; internships {stu.internships}; "
               f"skills {', '.join(stu.skill_list()) or 'none'}; readiness category {res.category}.")
        with st.spinner("Thinking..."):
            answer = bot.reply(msgs, stu, ctx)
        msgs.append({"role": "assistant", "content": answer})
        st.rerun()
