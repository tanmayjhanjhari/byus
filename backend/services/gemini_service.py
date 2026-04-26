"""
ByUs — Gemini AI Service

Wraps Google Gemini 2.0 Flash for:
  - Dataset scenario detection
  - Plain-English bias explanation for managers
  - Multi-turn Bias Copilot chat
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

_api_key = os.getenv("GEMINI_API_KEY", "")
if _api_key:
    genai.configure(api_key=_api_key)

_model = genai.GenerativeModel("gemini-2.0-flash")


class GeminiService:
    """Stateless wrapper around the Gemini 2.0 Flash model."""

    # ── Scenario detection ────────────────────────────────────────────────────

    def detect_scenario(self, columns: list[str]) -> dict[str, Any]:
        """
        Classify the dataset into one of: hiring, lending, healthcare,
        education, other.

        Returns
        -------
        dict with keys: scenario, confidence_pct, reason
        """
        prompt = (
            f"Dataset columns: {columns}. "
            "Classify into exactly one category: hiring, lending, healthcare, education, other. "
            'Return ONLY valid JSON with no markdown formatting: '
            '{"scenario": string, "confidence_pct": number, "reason": string}'
        )

        try:
            response = _model.generate_content(prompt)
            raw = response.text.strip()
            return self._parse_json(raw)
        except Exception:
            return {
                "scenario": "other",
                "confidence_pct": 50,
                "reason": "Could not detect scenario automatically.",
            }

    # ── Bias explanation ──────────────────────────────────────────────────────

    def explain_bias(
        self,
        metrics: dict[str, Any],
        sensitive_attr: str,
        scenario: str,
        plain_reason: str,
    ) -> str:
        """
        Generate a manager-friendly 3-paragraph explanation of the bias findings.

        Falls back to ``plain_reason`` if the Gemini API fails.
        """
        spd = metrics.get("spd", metrics.get("SPD", 0)) or 0
        di = metrics.get("di", metrics.get("DI", 1)) or 1
        severity = metrics.get("severity", "unknown")

        context = (
            f"Scenario: {scenario}. "
            f"Sensitive attribute: {sensitive_attr}. "
            f"SPD={spd:.3f}, DI={di:.3f}, severity={severity}. "
            f"Root cause analysis: {plain_reason}"
        )

        prompt = (
            f"You are ByUs AI, a bias auditing assistant. "
            f"Given this bias analysis: {context}. "
            "Write exactly 3 short paragraphs for a non-technical manager: "
            "1) What this bias means in plain words and concrete numbers. "
            "2) Why it likely exists — historical patterns, data collection, proxy variables. "
            "3) What real harm it causes to real people — be specific, human, and empathetic. "
            "Avoid all jargon. Do not use bullet points. Keep each paragraph under 4 sentences."
        )

        try:
            response = _model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            return plain_reason

    # ── Copilot chat ──────────────────────────────────────────────────────────

    def chat(
        self,
        user_message: str,
        history: list[dict[str, str]],
        session_context: dict[str, Any],
    ) -> str:
        """
        Multi-turn Bias Copilot conversation.

        Parameters
        ----------
        user_message : str
            The latest message from the user.
        history : list[dict]
            Previous turns as [{"role": "user"|"model", "content": str}, ...]
        session_context : dict
            Condensed analysis context injected as a system preamble.

        Returns
        -------
        str — Gemini's reply.
        """
        system_preamble = (
            "You are ByUs Bias Copilot, an expert AI assistant specialising in "
            "algorithmic fairness, bias detection, and ML ethics. "
            "Be concise, helpful, and explain fairness concepts in simple language. "
            f"Current analysis context: {json.dumps(session_context, default=str)}"
        )

        # Build Gemini-format history
        gemini_history: list[dict] = []

        # Inject system preamble as first model turn to simulate system instruction
        gemini_history.append(
            {"role": "user", "parts": ["Please confirm you understand your role."]}
        )
        gemini_history.append(
            {"role": "model", "parts": [system_preamble + " Understood — ready to assist."]}
        )

        for turn in history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if role in ("user", "model") and content:
                gemini_history.append({"role": role, "parts": [content]})

        try:
            chat_session = _model.start_chat(history=gemini_history)
            response = chat_session.send_message(user_message)
            return response.text.strip()
        except Exception:
            return "I'm having trouble connecting. Please try again."

    # ── JSON parsing helper ───────────────────────────────────────────────────

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        """Strip markdown code fences then parse JSON."""
        # Remove ```json ... ``` or ``` ... ``` fences
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract the first {...} block
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return {
            "scenario": "other",
            "confidence_pct": 50,
            "reason": "Could not parse Gemini response.",
        }
