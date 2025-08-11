from __future__ import annotations
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_mistralai.chat_models import ChatMistralAI

from .base import ResponseEngine
from core.config import settings


class MistralLangChainEngine(ResponseEngine):
    """
    Minimal LangChain + Mistral engine.
    - Uses ChatMistralAI via langchain-mistralai
    - Async via .ainvoke()
    - Only replies to text messages (others return None)
    """

    def __init__(self, cfg: dict[str, Any]):
        api_key = cfg.get("api_key") or settings.MISTRAL_API_KEY
        if not api_key:
            raise RuntimeError("MISTRAL_API_KEY is required for MistralLangChainEngine")

        model = cfg.get("model") or settings.MISTRAL_MODEL or "mistral-small-latest"
        temperature = float(cfg.get("temperature", 0.2))
        timeout = int(cfg.get("timeout", 20))
        max_retries = int(cfg.get("max_retries", 2))
        system = (
            cfg.get("system_prompt")
            or "You are a helpful WhatsApp assistant. Answer briefly."
        )

        llm = ChatMistralAI(
            api_key=api_key,
            model=model,  # param name is 'model' in ChatMistralAI
            temperature=temperature,
            max_retries=max_retries,
            timeout=timeout,
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                # You can include tenant metadata in the prompt if you want:
                ("human", "{user_input}"),
            ]
        )

        # Build a simple chain: Prompt -> LLM -> String
        self.chain = prompt | llm | StrOutputParser()

    async def reply(self, tenant_cfg: dict, message: dict) -> str | None:
        text = (message.get("text") or {}).get("body")
        if not text:
            return None

        # You could inject tenant info into the prompt here if desired
        result = await self.chain.ainvoke({"user_input": text})
        return (result or "").strip() or None
