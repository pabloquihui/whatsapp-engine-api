from __future__ import annotations
from typing import Any
from starlette.concurrency import run_in_threadpool
from openai import OpenAI
from .base import ResponseEngine
from core.config import settings


class OpenAIEngine(ResponseEngine):
    def __init__(self, cfg: dict[str, Any]):
        # allow per-tenant override; fall back to env
        api_key = cfg.get("api_key") or settings.model_dump().get("OPENAI_API_KEY")
        model = (
            cfg.get("model")
            or settings.model_dump().get("OPENAI_MODEL")
            or "gpt-4o-mini"
        )
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAIEngine")
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.system = (
            cfg.get("system_prompt")
            or "You are a helpful WhatsApp assistant. Answer briefly."
        )

    async def reply(self, tenant_cfg: dict, message: dict) -> str | None:
        # only reply to text; ignore others
        text = (message.get("text") or {}).get("body")
        if not text:
            return None

        def _call():
            return self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system},
                    {"role": "user", "content": text},
                ],
            )

        resp = await run_in_threadpool(_call)
        return (resp.choices[0].message.content or "").strip()
