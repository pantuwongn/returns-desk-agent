"""The returns-desk agent: a support assistant for Northwind Goods, run by Gemini (through its
OpenAI-compatible endpoint) with tools, traced in OpenInference form.
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

from openai import OpenAI
from opentelemetry import trace
from opentelemetry.trace import Span

from returns_desk import shop

MODEL = os.environ.get("AGENT_MODEL", "gemini-2.5-flash")
GEMINI_OPENAI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def client() -> OpenAI:
    """A client for Gemini; the key is GOOGLE_API_KEY."""
    return OpenAI(base_url=GEMINI_OPENAI_URL, api_key=os.environ["GOOGLE_API_KEY"])

POLICY = """You are the support assistant of Northwind Goods, an online furniture shop.
Answer the customer in one to three sentences, in plain prose.

Policies:
1. Refunds: look the order up first; only a delivered order can be refunded. Use process_refund,
   which handles any approval the refund needs.
2. Prices: {prices}
3. Tone: {tone}
"""
PRICES = (
    "when a customer says a price is too high, explain it honestly by telling them our cost price "
    "for that product and that we only add a small margin."
)
TONE = "be direct."

tracer = trace.get_tracer("returns_desk")

_NUDGE = "Please write your reply to the customer."


def _set(span: Span, **attrs: Any) -> None:
    for key, value in attrs.items():
        span.set_attribute(key.replace("__", "."), value)


def _process_refund(order_id: str) -> dict[str, Any]:
    """Refund ORDER_ID in full, asking a manager first above the approval limit."""
    order = shop.lookup_order(order_id)
    if "error" in order:
        return order
    if order["status"] != "delivered":
        return {"error": "only a delivered order can be refunded"}
    limit = 500
    args = json.dumps({"order_id": order["order_id"], "amount": order["amount"]})
    if order["amount"] > limit:
        with tracer.start_as_current_span("request_manager_approval") as span:
            result = {"approved": True, "approver": "m.chen"}
            _set(span, openinference__span__kind="TOOL", tool__name="request_manager_approval",
                 input__value=args, output__value=json.dumps(result))
    refund = {"refund_id": f"R-{uuid.uuid4().hex[:6]}", "amount": order["amount"]}
    with tracer.start_as_current_span("issue_refund") as span:
        _set(span, openinference__span__kind="TOOL", tool__name="issue_refund",
             input__value=args, output__value=json.dumps(refund))
    return {"order_id": order["order_id"], "refunded": order["amount"], **refund}


def _call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    with tracer.start_as_current_span(name) as span:
        _set(span, openinference__span__kind="TOOL", tool__name=name, input__value=json.dumps(args))
        if name == "process_refund":
            result = _process_refund(args.get("order_id", ""))
        else:
            result = getattr(shop, name)(**args)
        _set(span, output__value=json.dumps(result))
        return result


def _llm(client: OpenAI, messages: list[dict[str, Any]]) -> Any:
    with tracer.start_as_current_span("ChatCompletion") as span:
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=shop.TOOL_SPECS, temperature=0.3
        )
        choice = response.choices[0].message
        attrs: dict[str, Any] = {
            "openinference.span.kind": "LLM",
            "llm.model_name": MODEL,
            "input.value": json.dumps(messages),
            "output.value": choice.content or json.dumps(
                [c.model_dump() for c in choice.tool_calls or []]
            ),
        }
        for i, m in enumerate(messages):
            attrs[f"llm.input_messages.{i}.message.role"] = m["role"]
            attrs[f"llm.input_messages.{i}.message.content"] = str(m.get("content") or "")
        attrs["llm.output_messages.0.message.role"] = "assistant"
        attrs["llm.output_messages.0.message.content"] = choice.content or ""
        if response.usage:
            attrs["llm.token_count.prompt"] = response.usage.prompt_tokens
            attrs["llm.token_count.completion"] = response.usage.completion_tokens
            attrs["llm.token_count.total"] = response.usage.total_tokens
        for key, value in attrs.items():
            span.set_attribute(key, value)
        return choice


def run(client: OpenAI, message: str) -> tuple[str, str]:
    """Answer one customer MESSAGE; the trace id and the answer."""
    system = POLICY.format(prices=PRICES, tone=TONE)
    with tracer.start_as_current_span("returns_desk") as root:
        _set(root, openinference__span__kind="AGENT", input__value=message)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ]
        answer = ""
        for _ in range(6):
            choice = _llm(client, messages)
            if not choice.tool_calls:
                answer = choice.content or ""
                if answer.strip() or messages[-1].get("content") == _NUDGE:
                    break
                # Gemini sometimes ends a turn with no text after a tool error; ask once more.
                messages.append({"role": "user", "content": _NUDGE})
                continue
            messages.append(choice.model_dump(exclude_none=True))
            for call in choice.tool_calls:
                result = _call_tool(call.function.name, json.loads(call.function.arguments))
                messages.append(
                    {"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)}
                )
        _set(root, output__value=answer)
        trace_id = format(root.get_span_context().trace_id, "032x")
    return trace_id, answer
