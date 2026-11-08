"""Student and officer page for direct conversations."""
import streamlit as st

from services.message_service import MessageService
from ui.components import badge, bubble, empty_state, esc, html, page_header
from views.common import fmt_time, get_user


def render():
    """Render the message page for the current student or officer."""
    user = get_user()
    officer = user.role == "officer"
    page_header("Messages", "Talk directly with " + ("students" if officer else "the Career Office") + " inside GradPath AI")
    _render_messages(user.id, officer)


@st.fragment(run_every="5s")
def _render_messages(user_id: int, officer: bool):
    """Render conversation selection, message history, and the send form."""
    user = get_user()
    convs = MessageService.conversations(user_id)
    contacts = MessageService.contacts(user)
    labels = {c["partner_id"]: c for c in convs}

    if pre := st.session_state.pop("msg_partner", None):
        st.session_state["msg_active"] = pre
    ids = [c["partner_id"] for c in convs]
    active = st.session_state.get("msg_active")
    if active and active not in ids:
        ids.append(active)
    if ids and active not in ids:
        st.session_state["msg_active"] = ids[0]
    elif not ids:
        st.session_state.pop("msg_active", None)

    left, right = st.columns([1, 2.2], gap="large")
    with left:
        st.markdown("##### Conversations")
        if ids:
            def label(pid):
                """Format a conversation partner with any unread-message count."""
                c = labels.get(pid)
                if c:
                    return f'{c["name"]}' + (f' ({c["unread"]} new)' if c["unread"] else "")
                return contacts.get(pid, "New conversation").split(" (")[0].split(" - ")[0]
            st.radio("Conversations", ids, key="msg_active", format_func=label, label_visibility="collapsed")
        with st.expander("Start a new conversation", expanded=not ids):
            if not contacts:
                st.caption("Nobody to message yet.")
            else:
                pick = st.selectbox("Send to", list(contacts), format_func=lambda i: contacts[i], key="msg_new_pick",
                                    index=None, placeholder="Choose a person")
                if st.button("Open chat", key="msg_open") and pick:
                    st.session_state["msg_partner"] = pick
                    st.rerun()

    with right:
        active = st.session_state.get("msg_active")
        if not active:
            empty_state("No conversation selected", "Pick a conversation on the left, or start a new one.")
            return
        name = labels[active]["name"] if active in labels else contacts.get(active, "Conversation").split(" (")[0].split(" - ")[0]
        role = labels[active]["role"] if active in labels else ("Student" if officer else "Career Officer")
        html(f'<div class="gp-row" style="margin-bottom:.4rem"><b style="font-size:1.1rem">{esc(name)}</b>{badge(role, "violet" if role != "Student" else "info")}</div>')
        thread = MessageService.thread(user_id, active)
        with st.container(height=380, border=True):
            if not thread:
                st.caption("No messages yet. Say hello below.")
            for m in thread:
                html(bubble(m.body, fmt_time(m.created_at), m.sender_id == user_id))
        with st.form("send_msg", clear_on_submit=True):
            body = st.text_area("Message", height=90, max_chars=1500, label_visibility="collapsed", placeholder="Write a message...")
            if st.form_submit_button("Send message", type="primary"):
                ok, err = MessageService.send(user, active, body)
                if ok:
                    st.rerun()
                st.error(err)
