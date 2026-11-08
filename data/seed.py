"""Fictional demo data. Safe to run repeatedly: only inserts what is missing."""
import random

from core.config import (DEMO_OFFICER_EMAIL, DEMO_OFFICER_PASSWORD, DEMO_STUDENT_EMAIL,
                         DEMO_STUDENT_PASSWORD)
from core.database import session_scope
from core.models import (ActivityLog, CareerGoal, CareerOfficer, GoalTask, Job, JobApplication, Message,
                         Student)
from core.repositories import ApplicationRepository, JobRepository, MessageRepository, UserRepository
from data.career_requirements import CAREERS, DEPARTMENT_DEFAULT_CAREER
from services.auth_service import hash_password

FIRST = ["Ayesha", "Bilal", "Hira", "Usman", "Sana", "Hamza", "Zainab", "Daniyal", "Maryam", "Ali",
         "Fatima", "Omar", "Noor", "Saad", "Iqra", "Talha", "Areeba", "Ahmed", "Mahnoor", "Faizan",
         "Laiba", "Rayyan", "Anum", "Shahzaib"]
LAST = ["Khan", "Malik", "Siddiqui", "Raza", "Qureshi", "Ansari", "Sheikh", "Farooqui", "Baig", "Mirza"]
CERTS = ["Google Data Analytics", "AWS Cloud Practitioner", "Meta Front-End Basics", "IBM Python for DS",
         "Scrum Fundamentals", "ISTQB Foundation"]
DEPTS = list(DEPARTMENT_DEFAULT_CAREER)

JOBS = [
    ("Junior Python Developer", "NovaStack Labs", "Software Developer", "Entry Level", "Python,OOP,Git,SQL",
     "Build internal tools and REST services with a small, friendly engineering team.", "Karachi (Hybrid)"),
    ("Software Engineering Intern", "Brightpeak Systems", "Software Developer", "Internship", "Python,Data Structures,Git",
     "Summer internship working on feature development and unit tests.", "Remote"),
    ("Data Analyst Trainee", "Lumen Analytics", "Data Analyst", "Entry Level", "SQL,Excel,Data Visualization,Statistics",
     "Prepare weekly KPI dashboards and ad-hoc analyses for the sales team.", "Lahore (On-site)"),
    ("BI Reporting Intern", "Orbit Retail Group", "Data Analyst", "Internship", "SQL,BI Tools,Excel",
     "Support the BI team with data cleaning and Power BI reports.", "Karachi (Hybrid)"),
    ("Junior ML Engineer", "Cortexa AI", "Machine Learning Engineer", "Junior", "Python,Machine Learning,scikit-learn,Pandas",
     "Train and evaluate classical ML models and ship them as internal APIs.", "Remote"),
    ("Data Science Intern", "Helix Insights", "Machine Learning Engineer", "Internship", "Python,Pandas,Statistics",
     "Assist with feature engineering and experiment tracking.", "Islamabad (Hybrid)"),
    ("Front-End Developer", "Pixelforge Studio", "Web Developer", "Junior", "HTML/CSS,JavaScript,React,Git",
     "Craft responsive interfaces for client web apps.", "Karachi (On-site)"),
    ("Full-Stack Web Intern", "Cloudmint", "Web Developer", "Internship", "JavaScript,Node.js,REST APIs,SQL",
     "Work across the stack on a SaaS product for small businesses.", "Remote"),
    ("QA Automation Trainee", "Testwave Technologies", "QA Engineer", "Entry Level", "Test Automation,Selenium,Python,Bug Reporting",
     "Write automated regression suites and triage defects.", "Lahore (Hybrid)"),
    ("Manual QA Intern", "Safeline Software", "QA Engineer", "Internship", "Manual Testing,Bug Reporting,Jira,Agile",
     "Execute test plans and document defects clearly.", "Karachi (On-site)"),
    ("Backend Developer", "Streamline Fintech", "Software Developer", "Junior", "Python,REST APIs,SQL,Testing",
     "Develop secure payment-related APIs (fictional product).", "Remote"),
    ("Junior Data Analyst", "Greenleaf Health Data", "Data Analyst", "Junior", "SQL,Python,Pandas,Data Visualization",
     "Analyse anonymised operational data to improve scheduling.", "Islamabad (Hybrid)"),
]


def _seed_students(session, rng: random.Random):
    """Insert a reproducible set of fictional student profiles."""
    for i in range(24):
        dept = DEPTS[i % len(DEPTS)]
        career = DEPARTMENT_DEFAULT_CAREER[dept]
        req = list(CAREERS[career]["skills"])
        rng.shuffle(req)
        k = rng.randint(2, len(req) - 2)
        known, learning = req[:k], req[k:k + rng.randint(1, 2)]
        name = f"{FIRST[i]} {rng.choice(LAST)}"
        session.add(Student(
            email=f"{FIRST[i].lower()}.{i}@demo.gradpath.ai", name=name, password_hash=None,
            university="Demo University (fictional)", degree="BS", department=dept,
            graduation_year=rng.choice([2026, 2027]), cgpa=round(rng.uniform(2.1, 3.95), 2),
            skills=",".join(known), learning_skills=",".join(learning),
            certifications=",".join(rng.sample(CERTS, rng.randint(0, 3))),
            projects=rng.randint(0, 6), internships=rng.choices([0, 1, 2], [5, 3.5, 1.5])[0],
            work_experience_months=rng.choice([0, 0, 3, 6, 12]), communication=rng.randint(3, 10),
            extracurricular=rng.randint(1, 10), target_career=career, is_demo=True,
            phone="", city="Karachi",
        ))


def _seed_demo_student(session):
    """Create the sign-in demo student with sample goals and activity."""
    alex = Student(
        email=DEMO_STUDENT_EMAIL, name="Alex Morgan", password_hash=hash_password(DEMO_STUDENT_PASSWORD),
        university="Demo University (fictional)", degree="BS", department="Computer Science",
        graduation_year=2027, cgpa=3.35, skills="Python,SQL,Git,OOP,Problem Solving",
        learning_skills="Data Structures,REST APIs,Testing", certifications="Google Data Analytics",
        projects=3, internships=1, work_experience_months=4, communication=7, extracurricular=6,
        target_career="Software Developer", is_demo=True, phone="+923001234567", city="Karachi",
    )
    goal = CareerGoal(title="Become job-ready for Software Developer roles",
                      description="Sample goal created for the demo account.")
    goal.tasks = [GoalTask(title="Build a portfolio project with tests", done=True),
                  GoalTask(title="Learn REST API design", done=False),
                  GoalTask(title="Practise 30 data-structure problems", done=False),
                  GoalTask(title="Prepare for technical interviews", done=False)]
    alex.goals = [goal]
    session.add(alex)
    session.flush()
    for action, detail in [("Profile updated", "Added certifications"), ("Goal created", goal.title),
                           ("Resume analysed", "Software Developer - sample")]:
        session.add(ActivityLog(user_id=alex.id, actor_name=alex.name, action=action, detail=detail))


def seed_demo_data():
    """Add missing demo accounts, jobs, applications, and messages without overwriting data."""
    with session_scope() as s:
        users = UserRepository(s)
        if users.by_email(DEMO_OFFICER_EMAIL) is None:
            s.add(CareerOfficer(email=DEMO_OFFICER_EMAIL, name="Jordan Lee",
                                password_hash=hash_password(DEMO_OFFICER_PASSWORD)))
        if users.by_email(DEMO_STUDENT_EMAIL) is None:
            _seed_students(s, random.Random(42))
            _seed_demo_student(s)
        jobs = JobRepository(s)
        if jobs.count() == 0:
            for title, company, cat, level, skills, desc, loc in JOBS:
                jobs.add(Job(title=title, company=company, category=cat, level=level, skills=skills,
                             description=desc, location=loc, is_demo=True, is_open=True))
        s.flush()
        _seed_applications_and_messages(s)  # guarded: only inserts when there are none yet


def _seed_applications_and_messages(session):
    """Fictional applications and one welcome message so the officer pages are not empty on first launch."""
    from sqlalchemy import select
    from services.application_service import ApplicationService

    apps, msgs, users = ApplicationRepository(session), MessageRepository(session), UserRepository(session)
    jobs = list(session.scalars(select(Job)))
    if apps.count() == 0 and jobs:
        rng = random.Random(7)
        students = list(session.scalars(select(Student).where(Student.is_demo.is_(True)).limit(14)))
        for st_ in students:
            pool = [j for j in jobs if j.category == st_.target_career] or jobs
            job = rng.choice(pool)
            text = (f"{st_.name}. {st_.degree} in {st_.department}. Skills: {', '.join(st_.skill_list())}. "
                    f"Built {st_.projects} projects and completed {st_.internships} internship(s). Developed and tested "
                    "applications, improved results by 20% and collaborated in agile teams. " * 2)
            fit = ApplicationService.compute_fit(st_, job, text)
            apps.add(JobApplication(job_id=job.id, student_id=st_.id, phone="", availability=rng.choice(["Immediately", "Within 1 month"]),
                                    cover_note="Fictional demo application created for the project demonstration.",
                                    resume_text=text, status=rng.choice(["Submitted", "Submitted", "Under review", "Shortlisted"]), **fit))
    officer, alex = users.by_email(DEMO_OFFICER_EMAIL), users.by_email(DEMO_STUDENT_EMAIL)
    if officer and alex and msgs.count() == 0:
        msgs.add(Message(sender_id=officer.id, recipient_id=alex.id,
                         body="Welcome to GradPath AI! This is a demo message from the Career Office. Reply here to try the messaging feature."))
