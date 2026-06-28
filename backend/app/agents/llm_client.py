from __future__ import annotations
"""
Thin shared wrapper around Google Gemini (google-generativeai).

Centralizes model configuration and JSON parsing so the three AI agents
(LLM email parser, categorization fallback, merchant normalization) all share
a single, consistently-configured client.

The GEMINI_API_KEY is read from the environment. If it is missing, or the
library is not installed, the wrapper degrades gracefully: every call returns
None instead of raising, so callers can keep their non-LLM fallback paths.
"""
import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-2.5-flash"

# Module-level singletons. Initialized lazily on first use so importing this
# module never fails even when the dependency or API key is absent.
_model = None
_init_attempted = False


def _get_model():
    """Lazily construct (and cache) the Gemini model, or return None on failure."""
    global _model, _init_attempted
    if _init_attempted:
        return _model

    _init_attempted = True
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.warning("GEMINI_API_KEY is not set; LLM features are disabled.")
        return None

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        _model = genai.GenerativeModel(MODEL_NAME)
    except Exception as e:  # ImportError or configuration error
        logger.warning("Failed to initialize Gemini client: %s", e)
        _model = None
    return _model


# Matches a ```json ... ``` (or plain ``` ... ```) fenced block so we can strip
# Markdown fences the model sometimes wraps JSON in.
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)


def _extract_json(text: str) -> Optional[dict]:
    """Best-effort extraction of a single JSON object from raw model output."""
    if not text:
        return None

    candidate = text.strip()

    fence_match = _FENCE_RE.search(candidate)
    if fence_match:
        candidate = fence_match.group(1).strip()

    # Fall back to slicing from the first '{' to the last '}' if the response
    # has leading/trailing prose around the JSON object.
    if not candidate.startswith("{"):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start : end + 1]

    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        logger.debug("Could not parse JSON from model output: %r", text[:200])
        return None

    return parsed if isinstance(parsed, dict) else None


def ask_json(prompt: str) -> Optional[dict]:
    """Send `prompt` to Gemini and return the parsed JSON object, or None.

    Returns None on any failure (no API key, library missing, network error,
    or unparseable output). Retries once on transient errors.
    """
    model = _get_model()
    if model is None:
        return None

    last_error: Optional[Exception] = None
    # One initial attempt plus one retry on transient failures.
    for attempt in range(2):
        try:
            response = model.generate_content(prompt)
            text = getattr(response, "text", None)
            return _extract_json(text or "")
        except Exception as e:
            last_error = e
            logger.debug("Gemini request failed (attempt %d): %s", attempt + 1, e)

    logger.warning("Gemini request failed after retry: %s", last_error)
    return None


def ask_text(prompt: str) -> Optional[str]:
    """Send `prompt` to Gemini and return the raw stripped text, or None.

    Convenience helper for callers (categorizer, merchant normalizer) that want
    a single short string answer rather than a JSON object.
    """
    model = _get_model()
    if model is None:
        return None

    last_error: Optional[Exception] = None
    for attempt in range(2):
        try:
            response = model.generate_content(prompt)
            text = getattr(response, "text", None)
            return text.strip() if text else None
        except Exception as e:
            last_error = e
            logger.debug("Gemini request failed (attempt %d): %s", attempt + 1, e)

    logger.warning("Gemini request failed after retry: %s", last_error)
    return None
