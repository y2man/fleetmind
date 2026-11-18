"""Groq chat provider (OpenAI-compatible API). The key comes from backend settings only."""
from __future__ import annotations

import json
import logging

import httpx

from app.ai.providers.base import AIError, ChatResult, ToolCall

log = logging.getLogger("fleetmind.ai")


class GroqProvider:
    name = "groq"

    def __init__(self, *, api_key: str, model: str, base_url: str, reasoning_effort: str, timeout: float, max_tokens: int):
        self._key = api_key
        self.model = model
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._effort = reasoning_effort
        self._timeout = timeout
        self._max_tokens = max_tokens

    def chat(self, messages: list[dict], tools: list[dict] | None = None, *, max_tokens: int | None = None, temperature: float = 0.2) -> ChatResult:
        body: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens or self._max_tokens,
        }
        if self._effort in ("low", "medium", "high"):
            body["reasoning_effort"] = self._effort
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        try:
            res = httpx.post(self._url, json=body, headers={"Authorization": f"Bearer {self._key}"}, timeout=self._timeout)
        except httpx.TimeoutException:
            raise AIError(504, "The AI provider took too long to answer. Please try again.")
        except httpx.HTTPError:
            raise AIError(502, "Could not reach the AI provider. Check the server's internet access.")
        if res.status_code != 200:
            # Log the provider's error text (it never contains our key) but show the user a short message.
            log.warning("Groq returned %s: %s", res.status_code, res.text[:300])
            if res.status_code in (401, 403):
                raise AIError(502, "The AI provider rejected the API key. Check GROQ_API_KEY in the backend .env.")
            if res.status_code == 429:
                raise AIError(429, "The AI provider's rate limit was reached. Please try again in a moment.")
            if res.status_code == 404:
                raise AIError(502, f"The AI provider does not know the model '{self.model}'. Check GROQ_MODEL.")
            raise AIError(502, "The AI provider could not process the request.")
        try:
            msg = res.json()["choices"][0]["message"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise AIError(502, "The AI provider sent a response in an unexpected format.")
        calls: list[ToolCall] = []
        for i, tc in enumerate(msg.get("tool_calls") or []):
            fn = tc.get("function") or {}
            raw = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw) if isinstance(raw, str) else dict(raw)
                ok = isinstance(args, dict)
                args = args if ok else {}
            except (ValueError, TypeError):
                args, ok = {}, False
            calls.append(ToolCall(id=tc.get("id") or f"call_{i}", name=str(fn.get("name") or ""), arguments=args, valid_json=ok))
        return ChatResult(content=(msg.get("content") or "").strip(), tool_calls=calls)
