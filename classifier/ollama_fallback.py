"""
classifier/ollama_fallback.py — Stage 3: phi4-mini via Ollama local LLM.

Rules (from AGENTS.md):
- Always use the exact prompt template below.
- Set temperature=0.1 and num_predict=80 on every call.
- Always parse response as JSON.
- Retry once if JSON is invalid.
- If second attempt fails, return REVIEW — do not guess.
- Do not change the prompt without updating PROMPT_VERSION in config.py.
"""

import json
import logging

from .config import LLM_MODEL_NAME, LLM_NUM_PREDICT, LLM_TEMPERATURE, PROMPT_VERSION
from .schemas import EmailInput

logger = logging.getLogger(__name__)

# ── Prompt template — do NOT modify without bumping PROMPT_VERSION in config.py
_PROMPT_TEMPLATE = """\
You are an expense email classifier. Given the email details below, decide whether
it is an EXPENSE email, NOT an expense (NOT_EXPENSE), or uncertain (REVIEW).

Email subject: {subject}
Sender: {sender}
Body excerpt: {body_excerpt}

Respond ONLY with valid JSON in this exact format:
{{
  "label": "EXPENSE" | "NOT_EXPENSE" | "REVIEW",
  "confidence_band": "high" | "medium" | "low",
  "reason": "<one sentence explanation>"
}}
"""


def _build_prompt(email: EmailInput) -> str:
    return _PROMPT_TEMPLATE.format(
        subject=email.subject,
        sender=email.sender,
        body_excerpt=email.body[:500],
    )


def _parse_response(raw: str) -> dict:
    """Extract and validate JSON from LLM response."""
    raw = raw.strip()
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found in LLM response")
    data = json.loads(raw[start:end])
    allowed_labels = {"EXPENSE", "NOT_EXPENSE", "REVIEW"}
    if data.get("label") not in allowed_labels:
        raise ValueError(f"Invalid label: {data.get('label')}")
    return data


def _call_ollama(prompt: str) -> str:
    """Call phi4-mini via the ollama Python client."""
    import ollama  # type: ignore[import]
    response = ollama.generate(
        model=LLM_MODEL_NAME,
        prompt=prompt,
        options={"temperature": LLM_TEMPERATURE, "num_predict": LLM_NUM_PREDICT},
    )
    return response.get("response", "")


def classify(email: EmailInput) -> dict:
    """
    classify() wrapper for router compatibility.

    Same interface as distilbert_model.classify() so router.get_stage3_result()
    can call either backend uniformly.
    """
    return query(email)


def query(email: EmailInput) -> dict:
    """
    Query phi4-mini and return a classification dict.

    Returns:
        {
            "label": str,
            "confidence_band": str,
            "confidence_score": float,
            "reason": str,
            "prompt_version": str,
        }
    On two consecutive JSON failures, returns REVIEW.
    """
    prompt = _build_prompt(email)

    for attempt in range(1, 3):
        try:
            raw  = _call_ollama(prompt)
            data = _parse_response(raw)
            band = data.get("confidence_band", "low")
            score_map = {"high": 0.9, "medium": 0.7, "low": 0.35}
            return {
                "label":            data["label"],
                "confidence_band":  band,
                "confidence_score": score_map.get(band, 0.35),
                "reason":           data.get("reason", ""),
                "prompt_version":   PROMPT_VERSION,
            }
        except Exception as exc:
            logger.warning("LLM attempt %d failed: %s", attempt, exc)

    logger.error("Both LLM attempts failed — returning REVIEW")
    return {
        "label":           "REVIEW",
        "confidence_band": "low",
        "confidence_score": 0.0,
        "reason":          "LLM returned invalid JSON twice",
        "prompt_version":  PROMPT_VERSION,
    }
