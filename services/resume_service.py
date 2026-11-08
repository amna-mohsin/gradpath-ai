"""Transparent keyword-based resume analysis (no AI model, no external API)."""
import re
from typing import Dict, List

from data.career_requirements import CAREERS, SKILL_ALIASES

ACTION_VERBS = {"built", "developed", "designed", "implemented", "led", "created", "analysed", "analyzed",
                "improved", "automated", "deployed", "optimised", "optimized", "managed", "launched", "tested"}
SECTIONS = {"education": "Education", "experience": "Experience", "project": "Projects", "skill": "Skills"}


def _contains(text: str, alias: str) -> bool:
    """Find a keyword alias without matching it inside a larger token."""
    return re.search(r"(?<![a-z0-9+#.])" + re.escape(alias) + r"(?![a-z0-9+#])", text) is not None


class ResumeService:
    """Extract resume text and score keyword and structure coverage."""

    @staticmethod
    def skill_coverage(text: str, skills: List[str]) -> int:
        """Percentage of the given skills that appear (by keyword) in the text."""
        if not skills:
            return 0
        low = (text or "").lower()
        hit = sum(1 for sk in skills if any(_contains(low, a) for a in SKILL_ALIASES.get(sk, [sk.lower()])))
        return round(100 * hit / len(skills))

    @staticmethod
    def extract_text(uploaded_file) -> str:
        """Extract text from a PDF upload or decode a text upload as UTF-8."""
        if uploaded_file.name.lower().endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(uploaded_file)
            return "\n".join((p.extract_text() or "") for p in reader.pages)
        return uploaded_file.getvalue().decode("utf-8", errors="ignore")

    @staticmethod
    def analyze(text: str, career: str) -> Dict:
        """Compare resume keywords and structure with a career's requirements."""
        low = text.lower()
        found = [s for s, aliases in SKILL_ALIASES.items() if any(_contains(low, a) for a in aliases)]
        required = list(CAREERS[career]["skills"])
        matched = [s for s in required if s in found]
        missing = [s for s in required if s not in found]
        coverage = len(matched) / len(required)
        words = len(text.split())
        checks = [
            ("Contact email present", bool(re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text))),
            ("GitHub / LinkedIn / portfolio link", any(k in low for k in ("github", "linkedin", "portfolio"))),
            ("Measurable results (numbers or %)", bool(re.search(r"\d+\s?%|\b\d{2,}\b|\d+\+", text))),
            ("Strong action verbs (3+)", sum(1 for v in ACTION_VERBS if _contains(low, v)) >= 3),
            ("Length between 150 and 800 words", 150 <= words <= 800),
        ] + [(f"{label} section", key in low) for key, label in SECTIONS.items()]
        passed = sum(1 for _, ok in checks if ok)
        score = round(0.7 * coverage * 100 + 0.3 * (passed / len(checks)) * 100)
        tips: List[str] = []
        for label, ok in checks:
            if not ok:
                tips.append(f"Improve: {label.lower()}.")
        if missing:
            tips.insert(0, f"Add evidence for: {', '.join(missing[:5])} (only if you genuinely have them).")
        return {"score": score, "coverage": round(coverage * 100), "found": sorted(found), "matched": matched,
                "missing": missing, "checks": checks, "tips": tips, "words": words,
                "project_ideas": CAREERS[career]["projects"]}
