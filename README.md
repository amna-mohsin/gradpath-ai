# GradPath AI

<div align="center">

### Graduate Career Placement Prediction System

**A career-readiness platform that helps graduates understand their strengths, explore opportunities, and plan their next steps.**

Built with **Python, Streamlit, PostgreSQL, and scikit-learn**.

[Features](#-features) · [Technology](#-technology-stack) · [Setup](#-installation) · [Database](#-database-configuration) · [Model](#-placement-readiness-model) · [Project Structure](#-project-structure) · [Authors](#-authors)

</div>

---

## About

GradPath AI brings student career tools and Career Office workflows together in one web application. Students can review an estimate of placement readiness, identify skills to develop, explore career paths and job listings, apply with a PDF resume, track goals, and message the Career Office. Career officers can review student and application information, manage their own job listings, communicate with students, and view reports and model insights.

The application is designed as an educational project. Readiness estimates and job-fit scores are decision-support tools, not guarantees of employment or substitutes for human judgment.

## ✨ Features

### Student experience
- **Placement Readiness:** Estimate readiness from profile information, review contributing factors, and use the what-if simulator to explore possible profile changes.
- **Skill-Gap Analysis:** Compare a profile with illustrative career requirements and get skill-development guidance.
- **Career Explorer:** Browse example career paths, responsibilities, skills, projects, and preparation suggestions.
- **Job Opportunities:** Search listings and review skill-match information.
- **Applications:** Apply with a required PDF resume and at least one portfolio, GitHub, or LinkedIn link; track submitted applications.
- **Resume Analyzer:** Upload a PDF resume and review keyword coverage against a selected career.
- **Career Goals:** Set goals, track tasks, and monitor progress.
- **Messages:** Contact the Career Office through in-app messaging.

### Career Officer experience
- **Overview and student directory:** Review student and placement-readiness information.
- **Application review:** See applications ranked by job fit, from stronger to lower matches.
- **Job management:** Create and manage listings. Officers can edit or delete only their own non-demo listings; demonstration listings are read-only.
- **Reports and ML insights:** Review aggregate charts, model evaluation information, and plain-language chart explanations.
- **Messaging:** Communicate with students in the app.

### Security and account behavior
- Passwords are stored as PBKDF2 hashes.
- Officer registration requires an access code configured by the site owner.
- Browser sign-in can persist for up to 30 days or until sign-out.
- Demo accounts can be disabled for public deployments.

## 🧰 Technology Stack

| Area | Technologies |
|---|---|
| Application and UI | Python, Streamlit |
| Database | PostgreSQL (Neon) or local SQLite |
| ORM and persistence | SQLAlchemy |
| Machine learning | scikit-learn, pandas, NumPy, joblib |
| Charts | Plotly |
| Resume PDF reading | pypdf |
| Career assistant | Built-in rules or configured Groq, Gemini, OpenAI, or Anthropic API |
| Testing | pytest |

## 🏗️ Architecture and Design

The app is organized into a Streamlit presentation layer, service logic, repositories, and SQLAlchemy models:

1. **Views and UI** render the student and Career Officer pages and shared components.
2. **Services** implement account, prediction, application, messaging, resume, goal, and reporting workflows.
3. **Repositories** read and write domain records through SQLAlchemy.
4. **Models** define users, students, officers, jobs, applications, predictions, goals, tasks, activities, and messages.

The codebase demonstrates common object-oriented design concepts:

| Concept | Example |
|---|---|
| Inheritance | `User` with `Student` and `CareerOfficer` roles |
| Composition | `Student` goals and their `GoalTask` records |
| Association | `JobApplication` links a student to a job |
| Factory | `UserFactory`, `PredictorFactory`, and `ChatbotFactory` |
| Strategy | Rule-based and ML prediction strategies; rule-based and LLM chatbot strategies |
| Repository | Database access classes in `core/repositories.py` |

## 📁 Project Structure

```text
gradpath-ai/
├── app.py                  # Streamlit entry point, page routing, and access guards
├── core/                   # Configuration, database, models, repositories, validators
├── data/                   # Illustrative career requirements and demo seed data
├── ml/
│   ├── train_model.py      # Placement model training and evaluation
│   └── artifacts/          # Model artifact and evaluation metrics
├── services/               # Application and domain workflows
├── ui/                     # Shared theme, components, charts, and insights
├── views/                  # Student and Career Officer pages
├── tests/                  # pytest tests
├── requirements.txt
└── README.md
```

## 🚀 Installation

### Prerequisites

- Python 3.10 or later
- pip
- PostgreSQL/Neon if using a hosted database (optional; SQLite is the local fallback)

### Create an environment and install dependencies

```bash
git clone <your-repository-url>
cd gradpath-ai

python -m venv .venv
```

Activate the environment:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install dependencies and run the app:

```bash
pip install -r requirements.txt
streamlit run app.py
```

If `DATABASE_URL` is not configured, GradPath AI uses a local SQLite database. The app creates its tables, applies supported schema updates, and adds fictional demo records without deleting existing data.

### Demo accounts

| Role | Email | Password |
|---|---|---|
| Student | `demo@gradpath.ai` | `Demo@1234` |
| Career Officer | `officer@gradpath.ai` | `Officer@1234` |

These public demo credentials are for local evaluation. Disable demo login on a public deployment.

## 🔐 Configuration and Secrets

Create `.streamlit/secrets.toml` for local Streamlit settings, or add equivalent values in your deployment's secrets configuration. Never commit API keys, database passwords, or this file. The repository `.gitignore` excludes `.streamlit/secrets.toml` and `.env`.

Example configuration (replace placeholders with your own values):

```toml
DATABASE_URL = "postgresql://USER:PASSWORD@YOUR-NEON-HOST/neondb?sslmode=require"
OFFICER_ACCESS_CODE = "replace-with-a-private-registration-code"
ENABLE_DEMO_LOGIN = "false"

# Optional: enable the Groq career assistant
CHATBOT_PROVIDER = "groq"
GROQ_API_KEY = "your-groq-api-key"
GROQ_MODEL = "a-model-available-to-your-groq-account"
```

### Database configuration

1. Create a PostgreSQL database, for example a Neon project, and copy its connection string.
2. Set `DATABASE_URL` in the secrets file or hosting-provider settings. Use the provider's recommended SSL parameters.
3. Restart the app after changing configuration.

The app falls back to local SQLite when `DATABASE_URL` is absent. Database tables and supported updates are initialized by the application.

### Accounts and roles

Students register with their name, email, and password, then complete the onboarding profile. Career Officer registration also requires `OFFICER_ACCESS_CODE`. Officer sign-up is disabled if the code is not configured.

Set `ENABLE_DEMO_LOGIN = "false"` for a public deployment. Use a private officer access code and keep all database and AI credentials in the hosting platform's secret settings.

## 🤖 Placement Readiness Model

The readiness estimate can use the bundled model artifact or the built-in rule-based strategy. The trained ML model uses five inputs: normalized CGPA, completed projects, internship experience, communication score, and extracurricular score. Its output is a statistical estimate based on historical training data; it does not measure a student's full potential and does not guarantee employment.

### Train with a placement CSV

1. Obtain a placement dataset whose license permits your use, and save it as `ml/data/placement.csv`. The trainer accepts common column-name aliases; review `ALIASES` in `ml/train_model.py` if your CSV uses different names.
2. Run the full training workflow. It tunes all three candidate models; the full run may take several minutes:

   ```bash
   python -m ml.train_model --data ml/data/placement.csv
   ```

   Add `--fast` to skip hyperparameter search, or `--iters 8` to try fewer parameter settings per model. To generate a clearly labeled practice model instead:

   ```bash
   python -m ml.train_model --synthetic
   ```

   To compare the current five inputs with selected optional numeric columns in the CSV, run:

   ```bash
   python -m ml.train_model --data ml/data/placement.csv --compare-features
   ```

   This diagnostic does not change the model's features. In particular, IQ is sensitive personal information and must not be collected or used for student placement decisions.

3. The trainer creates an 80/20 stratified split, tunes Logistic Regression, Random Forest, and monotonic Gradient Boosting on training data, and selects using cross-validated ROC-AUC with a modest penalty for a large training/validation gap. The monotonic model constrains increases to the five model inputs not to lower its raw predicted score. It calibrates probabilities, selects an F1 threshold using out-of-fold predictions, and evaluates once on the untouched test set.
4. Training writes the model and metrics under `ml/artifacts/`. The app uses the saved model when available; the metrics support the model-insights page.

Evaluate more than accuracy: consider ROC-AUC, precision, recall, F1, calibration, and the observed placement rates for each readiness category. Dataset quality and representativeness matter. The bundled synthetic-data model is for practice and demonstration, not evidence of real-world placement performance.

After training, run `python -m ml.sanity_check` to probe example profiles, changes to individual inputs, and extreme profiles against the saved model. These are behavior checks only; passing them does not establish accuracy on real students.

## 💬 Career Assistant

The default `CHATBOT_PROVIDER = "rule"` uses built-in responses and needs no external API key. To use Groq, set `CHATBOT_PROVIDER`, `GROQ_API_KEY`, and `GROQ_MODEL` as in the secrets example. Choose a model currently available to your account. Gemini, OpenAI, and Anthropic providers are also supported with their corresponding credentials and model settings.

If no provider is configured, or an AI request fails, the assistant uses its built-in career guidance responses. Only configure providers with credentials you control; do not put keys in source code.

## ☁️ Deployment

GradPath AI can be deployed on Streamlit Community Cloud or another Streamlit-compatible host:

1. Push the project to your Git hosting provider.
2. Configure the app with `app.py` as its entry point.
3. Add database and other settings in the host's secrets configuration, not in committed files.
4. Set `ENABLE_DEMO_LOGIN = "false"` and a private `OFFICER_ACCESS_CODE` before making the app public.
5. Confirm the database connection and required schema are available, then test student and officer flows.

## 🧪 Tests

Run the test suite from the project root:

```bash
python -m pytest -q
```

The current tests cover validators, readiness scoring and categories, skill matching, resume coverage, application validation, listing ownership restrictions, and the Groq request integration. They use a temporary SQLite database where persistence is needed and do not require a live database or AI API.

## ⚠️ Limitations

- GradPath AI is an educational project and its authentication implementation is not a substitute for a production identity provider or a security review.
- Readiness estimates and application fit scores are informational aids, not hiring decisions or guarantees.
- Career requirements and seeded listings are illustrative demonstration content, not verified employer requirements or real vacancies.
- Demo student and officer accounts are fictional. Demo job listings are read-only, and fictional accounts cannot participate in real messaging.
- If real credentials were ever committed to Git, adding them to `.gitignore` does not remove them from repository history. Revoke and rotate exposed credentials.

## 👥 Authors

- **Amna Mohsin** — [GitHub](https://github.com/amna-mohsin) · [LinkedIn](https://www.linkedin.com/in/amna-m98/)
- **Hamna Ali Khan** — [GitHub](https://github.com/HamnaAliKhan)

## 📄 License

This project is licensed under the [MIT License](./LICENSE).

## 🎓 Academic Use

This project was developed for educational use. If you reuse or adapt it, credit the authors and follow your institution's academic-integrity requirements.
