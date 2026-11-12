"""GradPath AI - entry point. Run with:  streamlit run app.py"""
import os

# Must run before numpy/scikit-learn are imported. Shared hosts (e.g. Streamlit Cloud) report many CPU
# cores but only grant one or two; the model's parallel threads then fight each other and every
# single-row prediction becomes very slow. One thread is fastest for one-student predictions.
for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import extra_streamlit_components as stx  # noqa: E402
import streamlit as st  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402

st.set_page_config(page_title="GradPath AI", page_icon=":material/school:", layout="wide",
                   initial_sidebar_state="expanded")

from core.database import init_database  # noqa: E402
from core.models import Student  # noqa: E402
from core.config import demo_login_enabled  # noqa: E402
from services.auth_service import current_user, sync_demo_accounts  # noqa: E402
from ui.sidebar import render_sidebar  # noqa: E402
from ui.theme import inject_css  # noqa: E402
from views import (applications, assistant, career_explorer, goals, job_management, jobs,  # noqa: E402
                   landing, messages, ml_insights, officer_overview, onboarding, readiness, reports,
                   officer_profile, resume, skill_gap, student_overview, student_profile)


def _auth_cookie_manager():
    """Create the browser cookie manager used to restore persistent sign-in."""
    return stx.CookieManager(key="gradpath_auth_cookie_manager")


def _show_home(user) -> None:
    """Render the home page that matches the user's role and onboarding status."""
    if isinstance(user, Student) and not user.is_onboarded:
        onboarding.render()
    elif isinstance(user, Student):
        student_overview.render()
    else:
        officer_overview.render()


def _guarded(render_fn, role: str = "", allow_onboarding: bool = False):
    """Wrap a page renderer with authentication, role, and onboarding checks."""
    def run():
        """Check access and then render the requested page or the correct fallback."""
        user = current_user()
        if user is None:
            landing.render()
        elif isinstance(user, Student) and not user.is_onboarded:
            onboarding.render()
        elif allow_onboarding:
            _show_home(user)
        elif role and user.role != role:
            _show_home(user)
        else:
            render_fn()

    def safe_run():
        """Show a friendly, recoverable message instead of a raw traceback when a page fails.

        st.stop / st.rerun / st.switch_page raise BaseException subclasses, so they pass through untouched.
        """
        try:
            run()
        except OperationalError as exc:
            st.warning("The database is waking up or briefly unavailable. Please try again in a few seconds.")
            if st.button("Try again", type="primary", key="db_retry"):
                st.rerun()
            with st.expander("Technical details"):
                st.code(f"{type(exc).__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001 - last-resort page boundary
            st.error("Something went wrong while loading this page. Your data is safe; please try again.")
            if st.button("Reload page", key="page_retry"):
                st.rerun()
            with st.expander("Technical details"):
                st.exception(exc)
    return safe_run


def _profile():
    """Render the profile editor for the signed-in student's or officer's account."""
    user = current_user()
    if isinstance(user, Student):
        student_profile.render()
    else:
        officer_profile.render()


def _welcome():
    """Show the public landing page or redirect signed-in users to their home view."""
    user = current_user()
    if user is None:
        landing.render()
    else:
        _show_home(user)


def _role_pages(role: str, all_pages: dict) -> dict:
    """Select only the navigation pages available to the requested account role."""
    keys = (["overview", "applications", "job-management", "profile", "messages", "reports", "model"]
            if role == "officer" else
            ["overview", "profile", "readiness", "skill-gap", "careers", "jobs", "resume", "goals",
             "messages", "assistant", "model"])
    return {key: all_pages[key] for key in keys}


def build_pages(role: str) -> dict:
    """Register all app pages and return either role-specific or complete navigation."""
    P = st.Page
    all_pages = {
        "welcome": P(_guarded(_welcome), title="GradPath AI", url_path="welcome"),
        "overview": P(_guarded(lambda: _show_home(current_user())), title="Overview",
                      icon=":material/dashboard:", url_path="overview", default=True),
        "profile": P(_guarded(_profile), title="My Profile", icon=":material/person:", url_path="profile"),
        "readiness": P(_guarded(readiness.render, "student"), title="Placement Readiness",
                       icon=":material/speed:", url_path="readiness"),
        "skill-gap": P(_guarded(skill_gap.render, "student"), title="Skill-Gap Analysis",
                       icon=":material/compare_arrows:", url_path="skill-gap"),
        "careers": P(_guarded(career_explorer.render, "student"), title="Career Explorer",
                     icon=":material/explore:", url_path="careers"),
        "jobs": P(_guarded(jobs.render, "student"), title="Job Opportunities",
                  icon=":material/work:", url_path="jobs"),
        "resume": P(_guarded(resume.render, "student"), title="Resume Analyzer",
                    icon=":material/description:", url_path="resume"),
        "goals": P(_guarded(goals.render, "student"), title="Career Goals",
                   icon=":material/flag:", url_path="goals"),
        "messages": P(_guarded(messages.render), title="Messages", icon=":material/mail:", url_path="messages"),
        "assistant": P(_guarded(assistant.render, "student"), title="Career Assistant",
                       icon=":material/chat:", url_path="assistant"),
        "applications": P(_guarded(applications.render, "officer"), title="Applications",
                          icon=":material/assignment_ind:", url_path="applications"),
        "directory": P(_guarded(_welcome), title="Overview", url_path="directory"),
        "job-management": P(_guarded(job_management.render, "officer"), title="Job Management",
                            icon=":material/work:", url_path="job-management"),
        "reports": P(_guarded(reports.render, "officer"), title="Reports & Analytics",
                     icon=":material/bar_chart:", url_path="reports"),
        "model": P(_guarded(ml_insights.render), title="How the Estimate Works",
                   icon=":material/psychology:", url_path="model"),
        "onboarding": P(_guarded(onboarding.render, "student", allow_onboarding=True),
                        title="Set up your profile", url_path="onboarding"),
    }
    if role == "all":
        return all_pages
    return _role_pages(role, all_pages)


def main():
    """Initialise shared services, apply the theme, and run Streamlit navigation."""
    st.session_state["_auth_cookie_manager"] = _auth_cookie_manager()
    try:
        init_database()
        sync_demo_accounts(demo_login_enabled())
    except Exception as exc:
        inject_css()
        st.error("GradPath AI could not connect to the database.")
        st.markdown("Check `DATABASE_URL` in your secrets (Neon: include `?sslmode=require`). "
                    "On Neon's free tier the database may need a few seconds to wake up, so try again shortly.")
        with st.expander("Technical details"):
            st.code(f"{type(exc).__name__}: {exc}")
        st.stop()

    user = current_user()
    inject_css(hide_sidebar=user is None or isinstance(user, Student) and not user.is_onboarded)
    all_pages = build_pages("all")
    pages = _role_pages(user.role, all_pages) if user is not None else {}
    st.session_state["nav"] = pages
    if user is not None and (not isinstance(user, Student) or user.is_onboarded):
        render_sidebar(user, pages)
    pg = st.navigation(list(all_pages.values()), position="hidden")
    pg.run()


main()