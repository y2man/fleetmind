"""Provider-agnostic contract for chat models. A new provider only has to implement `chat`."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class AIError(Exception):
    """A problem the user should be told about. `message` is safe to show (never contains secrets)."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict
    valid_json: bool = True


@dataclass
class ChatResult:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)

    def assistant_message(self) -> dict:
        """The message to append to the history before sending tool results back."""
        import json

        msg: dict = {"role": "assistant", "content": self.content or None}
        if self.tool_calls:
            msg["tool_calls"] = [
                {"id": t.id, "type": "function", "function": {"name": t.name, "arguments": json.dumps(t.arguments)}}
                for t in self.tool_calls
            ]
        return msg


class AIProvider(Protocol):
    name: str
    model: str

    def chat(self, messages: list[dict], tools: list[dict] | None = None, *, max_tokens: int | None = None, temperature: float = 0.2) -> ChatResult: ...
