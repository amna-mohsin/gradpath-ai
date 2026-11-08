"""Career assistant.

STRATEGY PATTERN : ChatStrategy -> RuleBasedBot | LLMBot (Groq / Gemini / OpenAI / Anthropic via REST)
FACTORY PATTERN  : ChatbotFactory picks the strategy from CHATBOT_PROVIDER and falls back to rules.

Safety notes
- API keys are read from secrets only and sent in HTTP headers (never in the URL or on screen).
- Only anonymous profile numbers are sent as context (no name, email or phone).
- Each browser session is limited to MAX_LLM_CALLS AI replies so nobody can burn your free quota.
"""
from abc import ABC, abstractmethod
from typing import List, Optional

import requests
import streamlit as st

from core.config import get_setting
from core.models import Student

MAX_LLM_CALLS = 40

SYSTEM_PROMPT = (
    "You are GradPath AI's career assistant for university students. Give short, practical, encouraging "
    "advice about skills, projects, resumes, internships and interviews. Never promise employment or claim "
    "certainty about hiring outcomes. If asked about the app, mention its pages: Placement Readiness, "
    "Skill-Gap Analysis, Career Explorer, Job Opportunities, Resume Analyzer, Career Goals and Messages. "
    "Only discuss careers, studying, skills, jobs and this app; politely decline anything else. "
    "Keep answers under 150 words unless asked for more."
)

RULES = [
    (("improve", "readiness", "better", "ready"), "Open **Placement Readiness** to see which factors hold your score back. "
     "The 'biggest levers' section shows which improvement would raise your estimate the most."),
    (("skill", "learn", "gap"), "Open **Skill-Gap Analysis**, choose a career and focus on the top 'Missing' skills "
     "marked highest importance. Learn one skill at a time and prove it with a small project."),
    (("resume", "cv"), "Go to **Resume Analyzer**, upload your PDF, pick a target career and press *Analyze Resume*. "
     "It checks keywords and structure using transparent rules."),
    (("job", "internship", "vacanc", "opportunit", "apply"), "Open **Job Opportunities** to search listings, see your skill match, and press "
     "*Apply now* to send your application to the Career Office."),
    (("goal", "track", "task", "plan"), "Use **Career Goals** to create a goal, add small tasks, and tick them off. "
     "Progress updates automatically."),
    (("message", "contact", "officer"), "Use the **Messages** page to chat directly with the Career Office."),
    (("interview",), "Practise explaining 2 projects in 2 minutes each, rehearse common technical questions for your target role, "
     "and prepare 2 questions to ask the interviewer."),
    (("hello", "hi", "hey"), "Hi! I can help with career readiness, skills, resumes, jobs and goals. What would you like to work on?"),
]


def prepare_history(history: List[dict]) -> List[dict]:
    """Chat APIs need: only user/assistant roles, strictly alternating, starting with the user."""
    msgs: List[dict] = []
    for m in history:
        if m["role"] not in ("user", "assistant") or not str(m["content"]).strip():
            continue
        if msgs and msgs[-1]["role"] == m["role"]:
            msgs[-1]["content"] += "\n" + m["content"]
        else:
            msgs.append({"role": m["role"], "content": m["content"]})
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    return msgs


def explain_error(exc: Exception) -> str:
    """Return a concise, non-sensitive description of a chatbot API failure."""
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        code = exc.response.status_code
        hints = {400: "bad request or invalid API key", 401: "API key rejected", 403: "key not allowed for this API",
                 404: "model name not found - check *_MODEL in secrets", 429: "free-tier rate limit or quota reached"}
        return f"HTTP {code}: {hints.get(code, 'service error')}"
    if isinstance(exc, requests.Timeout):
        return "the AI service timed out"
    return type(exc).__name__


class ChatStrategy(ABC):
    """Define the interface shared by career-assistant reply providers."""

    label: str

    @abstractmethod
    def reply(self, messages: List[dict], student: Optional[Student], context: str) -> str:
        """Return a response to the conversation using the supplied profile context."""
        ...


class RuleBasedBot(ChatStrategy):
    """Provide built-in replies selected from simple career-topic keywords."""

    label = "Rule-based demo assistant"

    def reply(self, messages, student, context):
        """Choose the first matching built-in response for the latest message."""
        text = messages[-1]["content"].lower()
        for keys, answer in RULES:
            if any(k in text for k in keys):
                return answer
        return ("I can help with: improving readiness, choosing skills to learn, analysing your resume, finding jobs "
                "and tracking goals. Try one of the suggested questions.")


class LLMBot(ChatStrategy):
    """Request assistant replies from a configured language-model provider."""

    def __init__(self, provider: str):
        """Set the provider and initialize the built-in fallback responder."""
        self.provider = provider
        self.label = f"{provider.capitalize()} AI assistant"
        self.fallback = RuleBasedBot()

    def reply(self, messages, student, context):
        """Generate a provider reply, falling back when limited or unavailable."""
        used = st.session_state.get("llm_calls", 0)
        if used >= MAX_LLM_CALLS:
            return self.fallback.reply(messages, student, context) + "\n\n_(AI reply limit for this session reached - showing a built-in answer.)_"
        system = SYSTEM_PROMPT + ("\nStudent context (anonymous): " + context if context else "")
        history = prepare_history(messages)[-8:]
        while history and history[0]["role"] != "user":
            history.pop(0)
        try:
            if self.provider == "gemini":
                text = self._gemini(system, history)
            elif self.provider == "groq":
                text = self._groq(system, history)
            elif self.provider == "openai":
                text = self._openai(system, history)
            elif self.provider == "anthropic":
                text = self._anthropic(system, history)
            else:
                raise ValueError(f"Unsupported AI provider: {self.provider}")
            st.session_state["llm_calls"] = used + 1
            return text
        except Exception as exc:  # network, quota, bad key ...
            return (self.fallback.reply(messages, student, context) +
                    f"\n\n_(AI service unavailable - showing a built-in answer. Reason: {explain_error(exc)})_")

    def _gemini(self, system, history):
        """Send a formatted conversation to the Gemini generate-content API."""
        model = get_setting("GEMINI_MODEL", "gemini-2.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        body = {"system_instruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]} for m in history],
                "generationConfig": {"temperature": 0.6, "maxOutputTokens": 2048}}
        r = requests.post(url, headers={"x-goog-api-key": str(get_setting("GEMINI_API_KEY")), "Content-Type": "application/json"},
                          json=body, timeout=30)
        r.raise_for_status()
        data = r.json()
        parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()
        if not text:
            raise ValueError("empty response (the model may have blocked it)")
        return text

    def _groq(self, system, history):
        """Send a chat-completion request to the configured Groq model."""
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                          headers={"Authorization": f"Bearer {get_setting('GROQ_API_KEY')}",
                                   "Content-Type": "application/json"},
                          json={"model": get_setting("GROQ_MODEL", "llama-3.3-70b-versatile"),
                                "messages": [{"role": "system", "content": system}] + history,
                                "temperature": 0.6, "max_tokens": 2048}, timeout=30)
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
        if not isinstance(text, str) or not text.strip():
            raise ValueError("empty response")
        return text.strip()

    def _openai(self, system, history):
        """Send a chat-completion request to the configured OpenAI model."""
        r = requests.post("https://api.openai.com/v1/chat/completions",
                          headers={"Authorization": f"Bearer {get_setting('OPENAI_API_KEY')}"},
                          json={"model": get_setting("OPENAI_MODEL", "gpt-4o-mini"),
                                "messages": [{"role": "system", "content": system}] + history}, timeout=30)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def _anthropic(self, system, history):
        """Send a messages request to the configured Anthropic model."""
        r = requests.post("https://api.anthropic.com/v1/messages",
                          headers={"x-api-key": str(get_setting("ANTHROPIC_API_KEY")), "anthropic-version": "2023-06-01"},
                          json={"model": get_setting("ANTHROPIC_MODEL", "claude-haiku-5-5"), "max_tokens": 600,
                                "system": system, "messages": history}, timeout=30)
        r.raise_for_status()
        return r.json()["content"][0]["text"]


class ChatbotFactory:
    """Select an available language-model provider or the rule-based fallback."""

    KEYS = {"gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY",
            "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}

    @staticmethod
    def create() -> ChatStrategy:
        """Create a chatbot strategy using configured provider and API-key settings."""
        provider = str(get_setting("CHATBOT_PROVIDER", "rule")).lower()
        key_name = ChatbotFactory.KEYS.get(provider)
        if key_name and get_setting(key_name):
            return LLMBot(provider)
        return RuleBasedBot()