import os
import json
import asyncio
from typing import List, Any
import httpx
from autogen.tools import tool

async def search_serper(query: str, search_type: str = "search", **kwargs: Any) -> str:
    """
    Performs a search using the Serper API asynchronously.
    Args:
        query: The search query.
        search_type: The type of search to perform (e.g., 'news', 'search').
        **kwargs: Additional search parameters.
    Returns:
        A JSON string containing the search results.
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise ValueError("SERPER_API_KEY environment variable not set.")

    url = f"https://google.serper.dev/{search_type}"
    payload = {"q": query, **kwargs}
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as e:
        return f"Error using Serper API: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Error using Serper API: {e}"

async def search_serper_multiple(search_queries: List[str]) -> List[str]:
    """
    Performs multiple searches using the Serper API concurrently.
    Args:
        search_queries: A list of search queries.
    Returns:
        A list of JSON strings, each containing the search results for a query.
    """
    tasks = [search_serper(query=query) for query in search_queries]
    results = await asyncio.gather(*tasks)
    return results
