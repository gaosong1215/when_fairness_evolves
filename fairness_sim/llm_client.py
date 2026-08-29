"""Shared LLM client configuration."""

import os
from typing import Any


DEFAULT_MODEL_ENV = "FAIRNESS_MODEL"
BASE_URL_ENV = "FAIRNESS_BASE_URL"


class LazyLLMClient:
    """Initialize the OpenAI-compatible client only when it is first used."""

    def __init__(self):
        self._client = None

    def _load(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError(
                    "The openai package is required for LLM-backed runs. "
                    "Install it with: python3 -m pip install -r requirements.txt"
                ) from exc
            api_key = os.getenv("TURINGAI_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "Missing LLM API key. Set TURINGAI_API_KEY or OPENAI_API_KEY before running LLM-backed simulations."
                )

            base_url = os.getenv(BASE_URL_ENV) or os.getenv("TURINGAI_BASE_URL") or os.getenv("OPENAI_BASE_URL")
            if not base_url:
                raise RuntimeError(
                    f"Missing LLM base URL. Set {BASE_URL_ENV}, TURINGAI_BASE_URL, or OPENAI_BASE_URL."
                )

            self._client = OpenAI(api_key=api_key, base_url=base_url)
        return self._client

    def __getattr__(self, name):
        return getattr(self._load(), name)


def get_llm_client() -> LazyLLMClient:
    return LazyLLMClient()


def get_model_name() -> str:
    """Return the model selected by the experiment environment."""
    return os.getenv(DEFAULT_MODEL_ENV, "gpt-4o")
