from __future__ import annotations

from typing import Any

from openai import OpenAI

from app.config import settings


class LLMClient:

    def __init__(self):
        self.primary_client = self._create_client(
            settings.LLM_BASE_URL,
            settings.LLM_API_KEY
        )

        self.fallback_client = self._create_client(
            settings.FALLBACK_LLM_BASE_URL,
            settings.FALLBACK_LLM_API_KEY
        )

    def _create_client(
        self,
        base_url: str,
        api_key: str
    ) -> OpenAI | None:

        if not base_url or not api_key:
            return None

        return OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=30.0
        )

    def _call(
        self,
        client: OpenAI,
        model: str,
        messages: list[dict[str, str]]
    ) -> dict[str, Any]:

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
            max_tokens=1024
        )

        content = response.choices[0].message.content

        if not content:
            raise ValueError(
                "LLM returned an empty response."
            )

        return {
            "content": content,
            "model": model
        }

    def generate(
        self,
        messages: list[dict[str, str]]
    ) -> dict[str, Any]:

        # -------------------------------------------------
        # Primary LLM
        # -------------------------------------------------

        if self.primary_client and settings.LLM_MODEL:

            try:

                result = self._call(
                    client=self.primary_client,
                    model=settings.LLM_MODEL,
                    messages=messages
                )

                return {
                    **result,
                    "provider": "primary",
                    "fallback_used": False
                }

            except Exception as primary_error:

                primary_exception = str(
                    primary_error
                )

        else:

            primary_exception = (
                "Primary LLM is not configured."
            )

        # -------------------------------------------------
        # Fallback LLM
        # -------------------------------------------------

        if (
            self.fallback_client
            and settings.FALLBACK_LLM_MODEL
        ):

            try:

                result = self._call(
                    client=self.fallback_client,
                    model=settings.FALLBACK_LLM_MODEL,
                    messages=messages
                )

                return {
                    **result,
                    "provider": "fallback",
                    "fallback_used": True,
                    "primary_error": primary_exception
                }

            except Exception as fallback_error:

                raise RuntimeError(
                    "Both primary and fallback LLM calls failed. "
                    f"Primary error: {primary_exception}. "
                    f"Fallback error: {fallback_error}"
                )

        raise RuntimeError(
            "No usable LLM is configured. "
            f"Primary error: {primary_exception}"
        )
