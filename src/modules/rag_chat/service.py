from src.modules.rag_chat.llm_provider import LlmResponse, get_llm_provider


def build_answer(question: str, context: list[str]) -> LlmResponse:
    prompt = "\n".join([*context, question])
    return get_llm_provider().complete(prompt)
