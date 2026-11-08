"""Illustrative career requirements and skill aliases used by guidance features.

These examples are not verified employer requirements.
"""

CAREERS = {
    "Software Developer": {
        "icon": ":material/code:",
        "description": "Design, build and maintain software applications and services.",
        "responsibilities": ["Write clean, tested code", "Design APIs and data models",
                             "Review code and fix bugs", "Collaborate in agile teams"],
        "skills": {"Python": 3, "OOP": 3, "Data Structures": 3, "Git": 2, "SQL": 2,
                   "REST APIs": 2, "Testing": 2, "Problem Solving": 2, "Agile": 1},
        "preparation": ["Practise data-structure problems weekly", "Contribute to an open-source repo",
                        "Build one full-stack project end to end"],
        "projects": ["Task manager with REST API and tests", "Library management system (OOP + SQL)",
                     "CLI tool published on GitHub"],
    },
    "Data Analyst": {
        "icon": ":material/analytics:",
        "description": "Turn raw data into insights that guide business decisions.",
        "responsibilities": ["Clean and query datasets", "Build dashboards and reports",
                             "Run statistical analysis", "Present findings to stakeholders"],
        "skills": {"SQL": 3, "Excel": 2, "Python": 2, "Pandas": 2, "Statistics": 3,
                   "Data Visualization": 3, "BI Tools": 2, "Communication": 2},
        "preparation": ["Practise SQL joins and window functions", "Analyse a public dataset (Kaggle)",
                        "Publish a dashboard with a written summary"],
        "projects": ["Sales dashboard in Power BI/Tableau", "EDA report on a Kaggle dataset",
                     "SQL analysis of an e-commerce database"],
    },
    "Machine Learning Engineer": {
        "icon": ":material/psychology:",
        "description": "Build, evaluate and deploy machine-learning models.",
        "responsibilities": ["Prepare features and datasets", "Train and evaluate models",
                             "Deploy models behind APIs or apps", "Monitor model quality"],
        "skills": {"Python": 3, "Machine Learning": 3, "scikit-learn": 2, "Pandas": 2,
                   "Statistics": 3, "Deep Learning": 2, "Git": 1, "SQL": 1, "Docker": 1, "Cloud Basics": 1},
        "preparation": ["Complete an end-to-end ML project", "Learn model evaluation (ROC-AUC, F1, CV)",
                        "Deploy a model in a simple web app"],
        "projects": ["Placement or churn prediction model with evaluation report",
                     "Image classifier with a small demo app", "Recommendation system on movie data"],
    },
    "Web Developer": {
        "icon": ":material/web:",
        "description": "Create fast, accessible and engaging websites and web apps.",
        "responsibilities": ["Build responsive interfaces", "Connect front ends to APIs",
                             "Optimise performance", "Maintain web applications"],
        "skills": {"HTML/CSS": 3, "JavaScript": 3, "React": 2, "Node.js": 2, "REST APIs": 2,
                   "Git": 2, "SQL": 1, "Testing": 1},
        "preparation": ["Build and deploy a portfolio site", "Learn a front-end framework properly",
                        "Practise responsive design on real devices"],
        "projects": ["Personal portfolio website", "Blog with login and database",
                     "Weather or news app using a public API"],
    },
    "QA Engineer": {
        "icon": ":material/bug_report:",
        "description": "Ensure software quality through planned and automated testing.",
        "responsibilities": ["Design test cases and plans", "Automate regression tests",
                             "Report and track defects", "Work with developers on quality"],
        "skills": {"Manual Testing": 3, "Test Automation": 3, "Selenium": 2, "Bug Reporting": 2,
                   "SQL": 1, "Python": 1, "Agile": 2, "Jira": 1, "Communication": 2},
        "preparation": ["Write test cases for a real website", "Automate a login flow with Selenium",
                        "Practise writing clear bug reports"],
        "projects": ["Automated test suite for a demo web shop", "Test plan + bug reports for an open-source app",
                     "API tests with a REST client and scripts"],
    },
}

# canonical skill -> lowercase aliases used by the resume keyword matcher
SKILL_ALIASES = {
    "Python": ["python"], "Java": ["java"], "JavaScript": ["javascript", "js", "es6"],
    "C++": ["c++"], "SQL": ["sql", "mysql", "postgresql", "postgres", "sqlite"],
    "Git": ["git", "github", "gitlab"], "OOP": ["oop", "object-oriented", "object oriented"],
    "Data Structures": ["data structures", "algorithms", "dsa"],
    "HTML/CSS": ["html", "css", "html5", "css3", "tailwind", "bootstrap"],
    "React": ["react", "reactjs", "react.js"], "Node.js": ["node.js", "nodejs", "express"],
    "REST APIs": ["rest", "api", "apis", "restful", "fastapi", "flask", "django"],
    "Testing": ["unit test", "unit testing", "pytest", "junit", "testing"],
    "Pandas": ["pandas", "numpy"], "Statistics": ["statistics", "statistical", "hypothesis testing", "regression"],
    "Excel": ["excel", "spreadsheets", "pivot"], "Data Visualization": ["data visualization", "matplotlib", "plotly", "seaborn", "visualization"],
    "BI Tools": ["power bi", "tableau", "looker", "qlik"],
    "Machine Learning": ["machine learning", "ml", "classification", "clustering"],
    "scikit-learn": ["scikit-learn", "sklearn"], "Deep Learning": ["deep learning", "neural network", "tensorflow", "pytorch", "keras"],
    "Docker": ["docker", "container"], "Cloud Basics": ["aws", "azure", "gcp", "cloud"],
    "Manual Testing": ["manual testing", "test cases", "test plan"],
    "Test Automation": ["test automation", "automation testing", "cypress", "playwright"],
    "Selenium": ["selenium"], "Bug Reporting": ["bug report", "defect", "bug tracking"],
    "Agile": ["agile", "scrum", "kanban", "sprint"], "Jira": ["jira"],
    "Communication": ["communication", "presentation", "presented", "public speaking"],
    "Problem Solving": ["problem solving", "problem-solving", "leetcode", "competitive programming"],
    "Linux": ["linux", "bash", "shell"], "Teamwork": ["teamwork", "collaborat", "team lead", "led a team"],
}

SKILL_CATALOG = sorted(set(SKILL_ALIASES) | {s for c in CAREERS.values() for s in c["skills"]})

SKILL_CATEGORY = {
    "Programming": ["Python", "Java", "JavaScript", "C++", "OOP", "Data Structures", "Problem Solving"],
    "Data & Analytics": ["SQL", "Excel", "Pandas", "Statistics", "Data Visualization", "BI Tools"],
    "AI / ML": ["Machine Learning", "scikit-learn", "Deep Learning"],
    "Web & APIs": ["HTML/CSS", "React", "Node.js", "REST APIs"],
    "Quality & Tools": ["Git", "Testing", "Manual Testing", "Test Automation", "Selenium", "Bug Reporting",
                        "Docker", "Cloud Basics", "Linux", "Jira"],
    "Professional": ["Communication", "Teamwork", "Agile"],
}

DEPARTMENT_DEFAULT_CAREER = {
    "Computer Science": "Software Developer", "Software Engineering": "QA Engineer",
    "Data Science": "Machine Learning Engineer", "Information Technology": "Web Developer",
    "Electrical Engineering": "Software Developer", "Business Analytics": "Data Analyst",
}

LEARNING_TIPS = {
    "SQL": "Learn joins, GROUP BY and subqueries; practise on a sample database.",
    "Git": "Learn commits, branches and pull requests; push a project to GitHub.",
    "Statistics": "Cover distributions, hypothesis tests and regression basics.",
    "Python": "Build small programs, then a project that uses files, APIs and tests.",
    "Machine Learning": "Complete an end-to-end scikit-learn project with proper evaluation.",
    "Data Visualization": "Recreate charts with Plotly/Matplotlib and tell a story with them.",
}
