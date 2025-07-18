from dataclasses import dataclass
import os
import json
import asyncio
from typing import List, Any
import httpx
import requests


async def search_serper(
    query: str, 
    country: str = "us", 
    search_type: str = "search", 
    max_retries: int = 3,
    base_delay: float = 1.0,
    **kwargs: Any
):
    """
    Performs a search using the Serper API asynchronously with retry functionality.
    Args:
        query: The search query.
        search_type: The type of search to perform (e.g., 'news', 'search').
        max_retries: Maximum number of retry attempts (default: 3).
        base_delay: Base delay in seconds for exponential backoff (default: 1.0).
        **kwargs: Additional search parameters.
    Returns:
        A JSON string containing the search results.
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise ValueError("SERPER_API_KEY environment variable not set.")

    url = f"https://google.serper.dev/{search_type}"
    payload = {"q": query, "gl": country, **kwargs}
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    print(payload)
    print(url)
    print(headers)

    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=json.dumps(payload), headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            if attempt == max_retries:
                return f"Error using Serper API: {e.response.status_code} - {e.response.text}"
            
            # Retry on 5xx errors (server errors) and some 4xx errors that might be temporary
            if e.response.status_code >= 500 or e.response.status_code in [429, 408]:
                delay = base_delay * (2 ** attempt)
                print(f"Attempt {attempt + 1} failed with status {e.response.status_code}. Retrying in {delay:.2f} seconds...")
                await asyncio.sleep(delay)
                continue
            else:
                return f"Error using Serper API: {e.response.status_code} - {e.response.text}"
        except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadError) as e:
            if attempt == max_retries:
                return f"Network error using Serper API after {max_retries + 1} attempts: {e}"
            
            delay = base_delay * (2 ** attempt)
            print(f"Attempt {attempt + 1} failed with network error: {e}. Retrying in {delay:.2f} seconds...")
            await asyncio.sleep(delay)
            continue
        except Exception as e:
            return f"Unexpected error using Serper API: {e}"


@dataclass
class SerperQuery:
    q: str
    gl: str = "us"
    source_type: str = "search"

    def __post_init__(self):
        if self.source_type not in ["search", "news"]:
            self.source_type = "search"


async def search_serper_multiple(search_queries: List[SerperQuery]) -> List[dict]:
    """
    Performs multiple searches using the Serper API concurrently.
    Args:
        search_queries: A list of search queries.
        source_type: The type of search to perform ("search" or "news").
    Returns:
        A list of JSON strings, each containing the search results for a query.
    """
    print(f"Searching for {search_queries} with type")
    # DO not gather in a list, it will cause a memory error
    results = [
        await search_serper(query=query.q, country=query.gl, search_type=query.source_type)
        for query in search_queries
    ]
    return results


@dataclass
class ScraperQuery:
    query: str
    country_code: str = "us"
    tbs: str = "d"  # d for last 24 hours

    def __post_init__(self):
        if self.tbs not in ["d", "w", "m", "y"]:
            self.tbs = "d"


async def search_scraper_multiple(search_queries: List[SerperQuery]) -> List[dict]:
    """
    Performs multiple searches using the ScraperAPI concurrently.
    Args:
        search_queries: A list of search queries.
    Returns:
        A list of JSON responses, each containing the search results for a query.
    """
    print(f"Searching for {search_queries} with ScraperAPI")

    async def search_single(query: SerperQuery) -> dict:
        """Helper function to perform a single search"""
        api_key = os.getenv("SCRAPER_API_KEY")
        if not api_key:
            raise ValueError("SCRAPER_API_KEY environment variable not set.")

        payload = {
            "api_key": api_key,
            "query": query.q,
            "country_code": query.gl,
            "tbs": "d",
        }

        try:
            response = await asyncio.to_thread(
                requests.get,
                "https://api.scraperapi.com/structured/google/search",
                params=payload,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return f"Error using ScraperAPI: {e}"
        except Exception as e:
            return f"Error using ScraperAPI: {e}"

    tasks = [search_single(query) for query in search_queries]
    results = await asyncio.gather(*tasks)
    return results
