from dataclasses import dataclass


@dataclass(frozen=True)
class FetchedPage:
    url: str
    title: str | None
    content: str


async def fetch_page(url: str) -> FetchedPage:
    try:
        import httpx
    except ImportError as exc:
        raise RuntimeError("HTTP client is not installed") from exc

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url)
        response.raise_for_status()
        return FetchedPage(url=url, title=None, content=response.text)
