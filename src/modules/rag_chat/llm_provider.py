from dataclasses import dataclass
from typing import Protocol

import httpx

from src.core.config import get_settings


class ProviderConfigurationError(Exception):
    pass


class ProviderRequestError(Exception):
    pass


@dataclass(frozen=True)
class LlmResponse:
    content: str
    tokens_used: int = 0


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        pass


class LlmProvider(Protocol):
    def complete(self, prompt: str) -> LlmResponse:
        pass


class FakeEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), float(sum(map(ord, text)) % 997)] for text in texts]


class FakeLlmProvider:
    def complete(self, prompt: str) -> LlmResponse:
        content = (
            "Respuesta fake para desarrollo local. Contexto recibido:\n\n"
            f"{prompt[:1200]}"
        )
        return LlmResponse(content=content, tokens_used=len(prompt.split()))


class OpenAIEmbeddingProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = httpx.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": texts},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderRequestError("OpenAI embeddings request failed") from exc

        payload = response.json()
        data = sorted(payload.get("data", []), key=lambda item: item.get("index", 0))
        return [item["embedding"] for item in data]


class OpenAILlmProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def complete(self, prompt: str) -> LlmResponse:
        try:
            response = httpx.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": prompt},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderRequestError("OpenAI response request failed") from exc

        payload = response.json()
        usage = payload.get("usage") or {}
        output_text = payload.get("output_text")
        if output_text:
            return LlmResponse(
                content=output_text,
                tokens_used=usage.get("total_tokens", 0) or 0,
            )
        return LlmResponse(
            content=_extract_openai_text(payload),
            tokens_used=usage.get("total_tokens", 0) or 0,
        )


class GeminiEmbeddingProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model_name = f"models/{self.model}"
        requests = [
            {
                "model": model_name,
                "content": {"parts": [{"text": text}]},
            }
            for text in texts
        ]
        try:
            response = httpx.post(
                (
                    "https://generativelanguage.googleapis.com/v1beta/"
                    f"{model_name}:batchEmbedContents?key={self.api_key}"
                ),
                json={"requests": requests},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderRequestError("Gemini embeddings request failed") from exc

        payload = response.json()
        return [
            item["values"]
            for item in (
                embedding.get("embedding", {})
                for embedding in payload.get("embeddings", [])
            )
        ]


class GeminiLlmProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def complete(self, prompt: str) -> LlmResponse:
        try:
            response = httpx.post(
                (
                    "https://generativelanguage.googleapis.com/v1beta/"
                    f"models/{self.model}:generateContent?key={self.api_key}"
                ),
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderRequestError("Gemini generation request failed") from exc

        payload = response.json()
        usage = payload.get("usageMetadata") or {}
        return LlmResponse(
            content=_extract_gemini_text(payload),
            tokens_used=usage.get("totalTokenCount", 0) or 0,
        )


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    provider = settings.embedding_provider.lower()
    if provider == "fake":
        return FakeEmbeddingProvider()
    if provider == "openai":
        if not settings.openai_api_key:
            raise ProviderConfigurationError("OpenAI API key is not configured")
        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.embedding_model,
            timeout_seconds=settings.rag_request_timeout_seconds,
        )
    if provider == "gemini":
        api_key = settings.google_api_key or settings.gemini_api_key
        if not api_key:
            raise ProviderConfigurationError("Gemini API key is not configured")
        return GeminiEmbeddingProvider(
            api_key=api_key,
            model=settings.gemini_embedding_model,
            timeout_seconds=settings.rag_request_timeout_seconds,
        )
    raise ProviderConfigurationError(f"Unsupported embedding provider: {provider}")


def get_llm_provider() -> LlmProvider:
    settings = get_settings()
    provider = settings.llm_provider.lower()
    if provider == "fake":
        return FakeLlmProvider()
    if provider == "openai":
        if not settings.openai_api_key:
            raise ProviderConfigurationError("OpenAI API key is not configured")
        return OpenAILlmProvider(
            api_key=settings.openai_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.rag_request_timeout_seconds,
        )
    if provider == "gemini":
        api_key = settings.google_api_key or settings.gemini_api_key
        if not api_key:
            raise ProviderConfigurationError("Gemini API key is not configured")
        return GeminiLlmProvider(
            api_key=api_key,
            model=settings.gemini_model,
            timeout_seconds=settings.rag_request_timeout_seconds,
        )
    raise ProviderConfigurationError(f"Unsupported LLM provider: {provider}")


def _extract_openai_text(payload: dict) -> str:
    parts: list[str] = []
    for output in payload.get("output", []):
        for item in output.get("content", []):
            text = item.get("text")
            if text:
                parts.append(text)
    return "\n".join(parts).strip()


def _extract_gemini_text(payload: dict) -> str:
    parts: list[str] = []
    for candidate in payload.get("candidates", []):
        content = candidate.get("content") or {}
        for part in content.get("parts", []):
            text = part.get("text")
            if text:
                parts.append(text)
    return "\n".join(parts).strip()
