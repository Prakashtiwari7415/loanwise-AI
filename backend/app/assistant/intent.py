"""Intent routing and natural language classification for the LoanWise assistant."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class LanguagePreference(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"
    HINGLISH = "hinglish"


class QueryIntent(str, Enum):
    RATE_INQUIRY = "rate_inquiry"
    CALCULATION = "calculation"
    CONCEPTUAL = "conceptual"
    GENERAL = "general"


@dataclass(frozen=True)
class IntentAnalysis:
    """Classified intent and language preference of a user message."""

    intent: QueryIntent
    language: LanguagePreference
    loan_type: str | None  # "personal", "car", "home", or None
    is_rate_query: bool
    requires_financial_tools: bool


RATE_KEYWORDS = (
    "rate",
    "rates",
    "interest rate",
    "interest rates",
    "roi",
    "current rate",
    "latest rate",
    "market rate",
    "lender rate",
    "bank rate",
    "personal loan rate",
    "car loan rate",
    "home loan rate",
    "rate card",
    "lowest rate",
)

CALCULATION_KEYWORDS = (
    "calculate",
    "emi",
    "afford",
    "affordability",
    "prepay",
    "prepayment",
    "foreclosure",
    "amortization",
    "compare loan",
    "compare offers",
    "car expenses",
    "ownership cost",
    "fuel cost",
    "vehicle cost",
)

HINDI_PATTERNS = [
    r"[\u0900-\u097F]",  # Devanagari script range
    r"\b(?:hindi\s*(?:mein|me|bhasha)?|हिंदी)\b",
]

HINGLISH_PATTERNS = [
    r"\b(?:hinglish\s*(?:mein|me)?)\b",
    r"\b(?:batao|samjhao|kya\s+hai|kitna\s+hoga|kaise\s+kare|chahiye|hai\s+kya)\b",
]


def analyze_intent(message: str) -> IntentAnalysis:
    """Analyze the user's natural language message to determine intent and language."""
    msg_lower = message.lower().strip()

    # 1. Language detection
    language = LanguagePreference.ENGLISH
    if any(re.search(pat, message, re.IGNORECASE) for pat in HINDI_PATTERNS):
        if not re.search(r"\bhinglish\b", msg_lower):
            language = LanguagePreference.HINDI
        else:
            language = LanguagePreference.HINGLISH
    elif any(re.search(pat, msg_lower) for pat in HINGLISH_PATTERNS):
        language = LanguagePreference.HINGLISH

    # 2. Loan type detection
    loan_type = None
    if any(k in msg_lower for k in ("personal", "personal loan", "personal-loan")):
        loan_type = "personal"
    elif any(k in msg_lower for k in ("car", "auto", "vehicle", "car loan")):
        loan_type = "car"
    elif any(k in msg_lower for k in ("home", "housing", "home loan")):
        loan_type = "home"

    # 3. Intent detection
    is_rate_query = any(k in msg_lower for k in RATE_KEYWORDS)
    is_calc_query = any(k in msg_lower for k in CALCULATION_KEYWORDS)

    if is_rate_query:
        intent = QueryIntent.RATE_INQUIRY
        requires_financial_tools = True
    elif is_calc_query:
        intent = QueryIntent.CALCULATION
        requires_financial_tools = True
    elif any(k in msg_lower for k in ("what is", "explain", "kfs", "apr", "cooling-off", "fixed vs floating", "flat vs reducing", "rule", "circular")):
        intent = QueryIntent.CONCEPTUAL
        requires_financial_tools = False
    else:
        intent = QueryIntent.GENERAL
        requires_financial_tools = True

    return IntentAnalysis(
        intent=intent,
        language=language,
        loan_type=loan_type or ("personal" if is_rate_query else None),
        is_rate_query=is_rate_query,
        requires_financial_tools=requires_financial_tools,
    )
