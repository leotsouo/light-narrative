"""本地 LLM 提供者抽象（Ollama / Hugging Face）。"""
from __future__ import annotations

import abc
from typing import Any

import httpx

from src.config import (
    LLM_TIMEOUT_SECONDS,
    OLLAMA_BASE_URL,
    OLLAMA_DEFAULT_MODEL,
)


class BaseLLMProvider(abc.ABC):
    @abc.abstractmethod
    def complete(self, prompt: str, system: str | None = None) -> str:
        ...

    @abc.abstractmethod
    def is_available(self) -> bool:
        ...


class OllamaProvider(BaseLLMProvider):
    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_DEFAULT_MODEL,
        timeout: float = LLM_TIMEOUT_SECONDS,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            return r.status_code == 200
        except (httpx.HTTPError, OSError):
            return False

    def complete(self, prompt: str, system: str | None = None) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        r = httpx.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("message", {}).get("content", "")


class HuggingFaceProvider(BaseLLMProvider):
    """預留介面：需安裝 transformers + torch 後實作。"""

    def __init__(self, model_id: str = "meta-llama/Llama-3.2-3B-Instruct"):
        self.model_id = model_id
        self._pipeline = None

    def is_available(self) -> bool:
        try:
            import transformers  # noqa: F401
            return True
        except ImportError:
            return False

    def complete(self, prompt: str, system: str | None = None) -> str:
        if not self.is_available():
            raise RuntimeError("請安裝 transformers 與 torch 以使用 HuggingFace 提供者")
        raise NotImplementedError(
            "HuggingFaceProvider 為預留介面；MVP 請使用 Ollama。"
        )


def get_llm(provider: str = "ollama", **kwargs: Any) -> BaseLLMProvider:
    if provider == "huggingface":
        return HuggingFaceProvider(**kwargs)
    return OllamaProvider(**kwargs)
