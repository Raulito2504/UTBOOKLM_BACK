from dataclasses import dataclass


@dataclass(frozen=True)
class LlmResponse:
    content: str
    tokens_used: int = 0


class FakeEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), float(sum(map(ord, text)) % 997)] for text in texts]


class FakeLlmProvider:
    def complete(self, prompt: str) -> LlmResponse:
        return LlmResponse(content=prompt[:500], tokens_used=len(prompt.split()))


def get_embedding_provider() -> FakeEmbeddingProvider:
    return FakeEmbeddingProvider()


def get_llm_provider() -> FakeLlmProvider:
    return FakeLlmProvider()
