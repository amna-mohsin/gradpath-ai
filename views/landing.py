"""Public landing page with account access and a product overview."""
import pandas as pd
import streamlit as st

from core.config import (APP_FULL_NAME, DEMO_OFFICER_EMAIL, DEMO_OFFICER_PASSWORD, DEMO_STUDENT_EMAIL,
                         DEMO_STUDENT_PASSWORD, TAGLINE, VERSION, demo_login_enabled)
from core.validators import check_email
from services.auth_service import AuthService
from ui import charts
from ui.components import brand, esc, html, metric_card


def _sign_in_tab():
    """Render the sign-in form and authenticate submitted credentials."""
    with st.form("signin_form"):
        email = st.text_input("Email", placeholder="name@gmail.com", key="si_email")
        password = st.text_input("Password", type="password", key="si_pw")
        if st.form_submit_button("Sign in", type="primary"):
            err = check_email(email)
            if err:
                st.error(err)
            elif not password:
                st.error("Please enter your password.")
            else:
                user = AuthService.authenticate(email, password)
                if user:
                    AuthService.login(user)
                    st.rerun()
                st.error("We couldn't sign you in. Check your email and password, or create an account.")


def _signup_tab():
    """Render student or officer registration fields and submit new accounts."""
    role_label = st.radio("I am a...", ["Student", "Career Officer"], horizontal=True, key="signup_role")
    role = "officer" if role_label == "Career Officer" else "student"
    with st.form(f"signup_form_{role}"):
        name = st.text_input("Full name", max_chars=80, key=f"su_name_{role}")
        email = st.text_input("Email address", placeholder="name@gmail.com", key=f"su_email_{role}")
        office, code = "", ""
        if role == "officer":
            office = st.text_input("Office / organisation", placeholder="Demo University Career Office", key="su_office")
            code = st.text_input("Officer access code", type="password", key="su_code",
                                 help="Given to staff by your university's career office. It stops students creating officer accounts.")
        c1, c2 = st.columns(2)
        pw = c1.text_input("Password", type="password", help="At least 8 characters with a letter and a number", key=f"su_pw_{role}")
        pw2 = c2.text_input("Confirm password", type="password", key=f"su_pw2_{role}")
        if st.form_submit_button(f"Create {role_label.lower()} account", type="primary"):
            user, err = AuthService.register(role, name, email, pw, pw2, office, code)
            if err:
                st.error(err)
            else:
                AuthService.login(user)
                st.rerun()
    if role == "student":
        st.caption("After signing up you'll fill in your profile once, then go straight to your dashboard.")


def _demo_tab():
    """Render shortcuts for signing in to the configured demo accounts."""
    st.caption("Explore with fictional data. No sign-up needed.")
    if st.button("Explore as Student (Alex)", key="demo_student", type="primary"):
        user = AuthService.authenticate(DEMO_STUDENT_EMAIL, DEMO_STUDENT_PASSWORD)
        if user:
            AuthService.login(user)
            st.rerun()
    if st.button("Explore as Career Officer", key="demo_officer"):
        user = AuthService.authenticate(DEMO_OFFICER_EMAIL, DEMO_OFFICER_PASSWORD)
        if user:
            AuthService.login(user)
            st.rerun()


def render():
    """Render the public landing page, account forms, and feature overview."""
    html(f'''<div id="home"></div><div class="gp-nav">{brand(38)}<div>
        <a href="#home" target="_self">Home</a><a href="#features" target="_self">Features</a>
        <a href="#how" target="_self">How it works</a><a href="#about" target="_self">About</a>
        <a href="#get-started" target="_self">Get started</a></div></div>''')

    left, right = st.columns([1.2, 1], gap="large")
    with left:
        html(f'''<div class="gp-hero"><span class="gp-badge b-violet">{esc(APP_FULL_NAME)}</span>
            <h1>Your next opportunity <span>starts here.</span></h1>
            <p>Discover your career readiness, uncover skill gaps, and build a clearer path from university to employment with GradPath AI.</p>
            <a class="gp-btn primary" href="#get-started" target="_self">Check my career readiness</a>
            <a class="gp-btn ghost" href="#features" target="_self">Explore features</a>
            <div class="gp-muted" style="margin-top:1rem">{esc(TAGLINE)}</div></div>''')
    with right:
        html('<div id="get-started"></div>')
        with st.container(border=True):
            st.markdown("#### Get started")
            tabs = st.tabs(["Sign in", "Create account", "Quick demo"] if demo_login_enabled() else ["Sign in", "Create account"])
            with tabs[0]:
                _sign_in_tab()
            with tabs[1]:
                _signup_tab()
            if demo_login_enabled():
                with tabs[2]:
                    _demo_tab()

    html('<div class="gp-section">A look inside</div><div class="gp-muted">Sample preview with illustrative numbers.</div>')
    p1, p2, p3, p4 = st.columns([1, 1, 1, 1.6])
    with p1:
        html(metric_card("CGPA", "3.42", "Sample"))
    with p2:
        html(metric_card("Skill match", "72%", "Software Developer"))
    with p3:
        html(metric_card("Readiness", "Developing", "Demo estimate"))
    with p4:
        sample = pd.DataFrame({"Readiness": ["Needs Improvement"] * 5 + ["Developing"] * 11 + ["Job Ready"] * 8})
        charts.show(charts.readiness_donut(sample))

    html('<div id="features"></div><div class="gp-section">Everything you need to plan your path</div>')
    feats = [("Placement readiness", "Understand your current career readiness through a transparent estimate."),
             ("Skill-gap analysis", "Discover the skills you already have and the areas you could improve."),
             ("Career recommendations", "Explore career paths that align with your skills and interests."),
             ("Resume insights", "Identify useful keywords and areas to improve in your resume.")]
    for col, (t, d) in zip(st.columns(4), feats):
        with col:
            html(f'<div class="gp-card" style="min-height:150px"><h4>{t}</h4><p>{d}</p></div>')

    html('<div id="how"></div><div class="gp-section">How it works</div>')
    steps = [("Build your profile", "Add your academics, skills, projects and experience."),
             ("Explore your readiness", "See your estimate, strengths and gaps for your target career."),
             ("Plan your next move", "Follow recommended actions, apply to roles and track your goals.")]
    for col, (i, (t, d)) in zip(st.columns(3), enumerate(steps, 1)):
        with col:
            html(f'<div class="gp-card"><span class="gp-badge b-info">Step {i}</span><h4 style="margin-top:.5rem">{t}</h4><p>{d}</p></div>')

    html('<div id="about"></div><div class="gp-card" style="text-align:center;padding:2rem"><div class="gp-title" style="font-size:1.6rem">Your career journey deserves a plan.</div>'
         '<a class="gp-btn primary" href="#get-started" target="_self">Get started</a></div>')
    html(f'<div class="gp-footer"><b>{esc(APP_FULL_NAME)}</b> &middot; University OOAD demonstration project &middot; v{VERSION}<br>'
         'Demo records and job listings are fictional. Estimates are not guarantees of employment.</div>')
