"""One profile form, reused by the onboarding page and the My Profile page."""
from typing import Optional, Tuple

import streamlit as st

from core.config import CGPA_SCALE, DEGREES, DEPARTMENTS
from data.career_requirements import CAREERS, SKILL_CATALOG
from services.student_service import StudentService


def _idx(options, value) -> Optional[int]:
    """Return a selectbox index only when the current value is in its options."""
    return options.index(value) if value in options else None


def profile_form(stu, key: str, submit_label: str, show_cancel: bool = False) -> Tuple[Optional[str], Optional[dict]]:
    """Renders the form. Returns ("save", record) after successful validation, ("cancel", None) or (None, None)."""
    with st.form(f"{key}_form"):
        st.markdown("##### 1. About you")
        c1, c2 = st.columns(2)
        name = c1.text_input("Full name *", value=stu.name, max_chars=80, key=f"{key}_name")
        phone = c2.text_input("Phone number *", value=stu.phone or "", max_chars=20, key=f"{key}_phone",
                              placeholder="+923001234567", help="Used only when you apply for jobs, so the Career Office can reach you.")
        c1, c2 = st.columns(2)
        city = c1.text_input("City *", value=stu.city or "", max_chars=60, key=f"{key}_city", placeholder="Karachi")
        portfolio = c2.text_input("Portfolio / GitHub / LinkedIn (optional)", value=stu.portfolio_url or "", max_chars=200,
                                  key=f"{key}_url", placeholder="https://github.com/yourname")

        st.markdown("##### 2. Academic information")
        c1, c2 = st.columns(2)
        university = c1.text_input("University *", value=stu.university or "", max_chars=120, key=f"{key}_uni")
        degree = c2.selectbox("Degree *", DEGREES, index=_idx(DEGREES, stu.degree), placeholder="Choose your degree", key=f"{key}_deg")
        c1, c2, c3 = st.columns(3)
        department = c1.selectbox("Department *", DEPARTMENTS, index=_idx(DEPARTMENTS, stu.department),
                                  placeholder="Choose your department", key=f"{key}_dept")
        year = c2.number_input("Graduation year", 2024, 2035, int(stu.graduation_year or 2027), key=f"{key}_year")
        cgpa = c3.number_input(f"CGPA (0 - {CGPA_SCALE:g}) *", 0.0, float(CGPA_SCALE), float(stu.cgpa or 0.0), 0.01,
                               format="%.2f", key=f"{key}_cgpa", help="Your cumulative grade point average.")

        st.markdown("##### 3. Skills and career goal")
        target = st.selectbox("Target career *", list(CAREERS), index=_idx(list(CAREERS), stu.target_career),
                              placeholder="What do you want to become?", key=f"{key}_target")
        skills = st.multiselect("Skills I am confident in *", SKILL_CATALOG, default=[s for s in stu.skill_list() if s in SKILL_CATALOG],
                                key=f"{key}_skills", placeholder="Pick all that apply")
        learning = st.multiselect("Skills I am still learning", SKILL_CATALOG, default=[s for s in stu.learning_list() if s in SKILL_CATALOG],
                                  key=f"{key}_learning", help="These count as partial credit in Skill-Gap Analysis.")

        st.markdown("##### 4. Experience and activities")
        c1, c2, c3 = st.columns(3)
        projects = c1.number_input("Completed projects", 0, 50, int(stu.projects or 0), key=f"{key}_proj")
        internships = c2.number_input("Internships", 0, 10, int(stu.internships or 0), key=f"{key}_intern")
        months = c3.number_input("Work experience (months)", 0, 120, int(stu.work_experience_months or 0), key=f"{key}_months")
        certs = st.text_input("Certifications (comma separated)", value=stu.certifications or "", key=f"{key}_certs",
                              placeholder="Google Data Analytics, AWS Cloud Practitioner")
        c1, c2 = st.columns(2)
        comm = c1.slider("Communication skills (1 = beginner, 10 = excellent)", 1, 10, int(stu.communication or 5), key=f"{key}_comm")
        extra = c2.slider("Extracurricular / leadership activity (0 - 10)", 0, 10, int(stu.extracurricular or 0), key=f"{key}_extra")

        b1, b2, _ = st.columns([1.4, 1, 3])
        save = b1.form_submit_button(submit_label, type="primary")
        cancel = b2.form_submit_button("Cancel changes") if show_cancel else False

    if cancel:
        return "cancel", None
    if save:
        data = dict(name=name, phone=phone, city=city, portfolio_url=portfolio, university=university, degree=degree,
                    department=department, graduation_year=year, cgpa=cgpa, target_career=target, skills=skills,
                    learning=learning, projects=projects, internships=internships, months=months,
                    certifications=[c.strip() for c in certs.split(",") if c.strip()], communication=comm,
                    extracurricular=extra)
        errors = StudentService.validate_profile(data)
        if errors:
            for e in errors:
                st.error(e)
            return None, None
        return "save", StudentService.to_record(data)
    return None, None
