from datetime import datetime
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from urllib.parse import urljoin, urlparse
import json
import asyncio
import newspaper
import nltk

try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab")


async def visit_urls_and_extract_content(urls: List[str]) -> str:
    """
    Asynchronously visit a list of URLs using Playwright and extract content and URLs.
    Args:
        urls: The list of URLs to visit.
    Returns:
        JSON string containing a list of dictionaries with extracted data for each URL.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        tasks = [_visit_and_extract(context, url) for url in urls]
        results = await asyncio.gather(*tasks)
        await browser.close()
    return json.dumps(results, indent=2)


async def _visit_and_extract(context, url: str) -> Dict[str, Any]:
    """Visit a single URL in a new page and extract its data."""
    page = await context.new_page()
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=10000)
        if not response or response.status >= 400:
            return {
                "error": f"Failed to load page. Status: {response.status if response else 'Unknown'}",
                "url": url,
            }

        content = await page.content()
        article = newspaper.Article(url)
        article.set_html(content)
        article.parse()
        article.nlp()

        result = {
            "title": article.title,
            "text": article.text,
            "top_image": article.top_image,
            "authors": article.authors,
            "summary": article.summary,
            "keywords": article.keywords,
            "publish_date": article.publish_date.strftime("%Y-%m-%d")
            if type(article.publish_date) is datetime
            else article.publish_date,
            "article_url": article.url,
            "source_url": article.source_url,
        }
    except Exception as e:
        result = {"error": f"Playwright error: {str(e)}", "url": url}
    finally:
        await page.close()
    return result


if __name__ == "__main__":

    async def main():
        # The tool expects a list of URLs for the 'urls' argument.
        result = await visit_urls_and_extract_content(
            urls=[
                "https://www.tbsnews.net/bangladesh/politics/fakhrul-alleges-conspiracy-eliminate-tarique-politics-1187346"
            ]
        )
        print(result)

    asyncio.run(main())
