"""The question-answering loop: the model asks for data tools, we run them, it writes the answer."""
from __future__ import annotations

import json

from app.ai.prompts import assistant_system_prompt
from app.ai.providers.base import AIError, AIProvider
from app.ai.tools import ToolContext, run_tool, tool_schemas
from app.core.config import get_settings

EMPTY_ANSWER = "I couldn't put together an answer. Try rephrasing the question or asking about something more specific."


def ask(db, user, question: str, history: list[dict], provider: AIProvider) -> dict:
    ctx = ToolContext(db, user)
    tools = tool_schemas(user)
    max_rounds = get_settings().ai_max_tool_rounds
    messages: list[dict] = [{"role": "system", "content": assistant_system_prompt(user.organization.name, ctx.now)}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history if m["role"] in ("user", "assistant")]
    messages.append({"role": "user", "content": question})

    used: list[dict] = []
    for round_no in range(max_rounds + 1):
        final_round = round_no == max_rounds  # no tools on the last round, so the model has to answer
        result = provider.chat(messages, None if final_round or not tools else tools)
        if not result.tool_calls:
            return {"answer": result.content or EMPTY_ANSWER, "tools_used": used}
        messages.append(result.assistant_message())
        for call in result.tool_calls:
            out = run_tool(ctx, call.name, call.arguments) if call.valid_json else json.dumps({"error": "Tool arguments were not valid JSON."})
            used.append({"name": call.name.split(".")[-1], "arguments": call.arguments})
            messages.append({"role": "tool", "tool_call_id": call.id, "content": out})
    raise AIError(502, "The assistant did not finish. Please try again.")  # unreachable in practice
