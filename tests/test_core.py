"""Run with:  pip install pytest  &&  python -m pytest -q
These tests need no database or network."""
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from core.models import Base, Job
from core.repositories import JobRepository
from core.validators import (check_email, check_name, check_password, check_phone, check_url)
from services.application_service import ApplicationService, fit_label
from services.chatbot_service import ChatbotFactory, LLMBot
from services.job_service import JobService
from services.prediction_service import RuleBasedStrategy, categorize
from services.resume_service import ResumeService
from services.skill_gap_service import SkillGapService


def make_student(**kw):
    """Build a lightweight student-like object for service unit tests."""
    base = dict(cgpa=3.2, projects=3, internships=1, communication=7, extracurricular=5,
                _skills=["Python", "SQL", "Git"], _learning=["OOP"], _certs=["Cert A"])
    base.update(kw)
    ns = SimpleNamespace(**base)
    ns.skill_list = lambda: ns._skills
    ns.learning_list = lambda: ns._learning
    ns.cert_list = lambda: ns._certs
    return ns


def test_validators():
    """Check accepted and rejected examples for the shared input validators."""
    assert check_email("name@gmail.com") is None
    assert check_email("bad@") is not None
    assert check_password("abc12345") is None
    assert check_password("abcdefgh") is not None
    assert check_password("abc12345", "different1") is not None
    assert check_phone("+923001234567") is None
    assert check_phone("12345") is not None
    assert check_name("Amna Mohsin") is None
    assert check_name("A1") is not None
    assert check_url("") is None and check_url("https://github.com/me") is None
    assert check_url("github.com/me") is not None


def test_rule_based_is_deterministic_and_monotonic():
    """Ensure the demo predictor is repeatable and rewards improved experience."""
    s = make_student()
    a, b = RuleBasedStrategy().predict(s), RuleBasedStrategy().predict(s)
    assert a.probability == b.probability
    better = RuleBasedStrategy().predict(make_student(projects=6, internships=2))
    assert better.probability > a.probability


def test_categories():
    """Verify readiness labels at category boundaries and custom thresholds."""
    assert categorize(10) == "Needs Improvement"
    assert categorize(55) == "Developing"
    assert categorize(90) == "Job Ready"
    assert categorize(30, (20, 40)) == "Developing"


def test_skill_gap_and_resume():
    """Check career skill matching and resume keyword coverage calculations."""
    g = SkillGapService.analyze(make_student(), "Software Developer")
    assert 0 < g["match"] < 100
    assert SkillGapService.match_job_skills(make_student(), ["Python", "Docker"]) == 50
    assert ResumeService.skill_coverage("I know Python and SQL", ["Python", "SQL", "Git"]) == 67


def test_fit_label():
    """Check the human-readable labels assigned to application fit scores."""
    assert fit_label(80)[0] == "Strong fit"
    assert fit_label(10)[0] == "Low fit"


def test_application_requires_resume_and_profile_link():
    """Require a valid PDF and at least one professional profile link."""
    details = {
        "phone": "+923001234567",
        "availability": "Immediately",
        "portfolio_url": "",
        "cover_note": "I am interested in this role and believe my experience and skills are a strong match.",
        "resume_text": " ".join(["resume"] * 40),
        "resume_pdf": b"%PDF-1.7\nsample",
        "consent": True,
    }
    errors = ApplicationService.validate(details)
    assert any("portfolio, GitHub or LinkedIn" in error for error in errors)
    assert not any("resume" in error.lower() for error in errors)
    details["portfolio_url"] = "https://github.com/student"
    assert ApplicationService.validate(details) == []
    details["resume_pdf"] = b"not a pdf"
    assert any("valid PDF" in error for error in ApplicationService.validate(details))


def test_job_listing_changes_are_limited_to_owner_and_non_demo_listings():
    """Prevent edits and deletions of another officer's or a demo listing."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        owner_job = Job(title="Owner listing", company="Company A", category="Technology",
                        level="Entry Level", created_by=11)
        other_job = Job(title="Other listing", company="Company B", category="Technology",
                        level="Entry Level", created_by=22)
        demo_job = Job(title="Demo listing", company="Company C", category="Technology",
                       level="Entry Level", created_by=11, is_demo=True)
        session.add_all([owner_job, other_job, demo_job])
        session.flush()
        repo = JobRepository(session)

        assert repo.update_manageable(owner_job.id, 11, {"title": "Updated listing"})
        assert owner_job.created_by == 11
        assert not repo.update_manageable(other_job.id, 11, {"title": "Unauthorized edit"})
        assert not repo.delete_manageable(other_job.id, 11)
        assert not repo.update_manageable(demo_job.id, 11, {"title": "Demo edit"})
        assert not repo.delete_manageable(demo_job.id, 11)
        assert repo.delete_manageable(owner_job.id, 11)

    with pytest.raises(ValueError, match="unsupported fields"):
        JobService.update(1, {"created_by": 11}, 11)


def test_groq_chatbot_uses_groq_api_and_model(monkeypatch):
    """Verify chatbot requests use the configured Groq URL, model, and API key."""
    import services.chatbot_service as chatbot_service

    calls = {}

    class Response:
        """Minimal successful HTTP response returned by the mocked Groq request."""

        def raise_for_status(self):
            """Match requests.Response.raise_for_status for a successful response."""
            pass

        def json(self):
            """Return the representative chat-completion payload."""
            return {"choices": [{"message": {"content": "Try a focused portfolio project."}}]}

    def fake_post(url, **kwargs):
        """Capture the outgoing request and return a deterministic fake response."""
        calls.update(url=url, **kwargs)
        return Response()

    monkeypatch.setattr(chatbot_service.requests, "post", fake_post)
    monkeypatch.setattr(chatbot_service, "get_setting",
                        lambda name, default=None: {"GROQ_API_KEY": "test-key", "GROQ_MODEL": "test-model"}.get(name, default))
    monkeypatch.setattr(chatbot_service.st, "session_state", {"llm_calls": 0})

    bot = LLMBot("groq")
    answer = bot.reply([{"role": "user", "content": "How can I build a portfolio?"}], None, "")

    assert answer == "Try a focused portfolio project."
    assert bot.label == "Groq AI assistant"
    assert calls["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert calls["headers"]["Authorization"] == "Bearer test-key"
    assert calls["json"]["model"] == "test-model"
    assert calls["json"]["messages"][0]["role"] == "system"
    monkeypatch.setattr(chatbot_service, "get_setting",
                        lambda name, default=None: {"CHATBOT_PROVIDER": "groq",
                                                    "GROQ_API_KEY": "test-key"}.get(name, default))
    assert isinstance(ChatbotFactory.create(), LLMBot)
