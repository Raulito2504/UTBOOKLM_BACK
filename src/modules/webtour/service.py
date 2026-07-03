from src.modules.webtour.fetcher import FetchedPage, fetch_page


async def fetch_source(url: str) -> FetchedPage:
    return await fetch_page(url)
