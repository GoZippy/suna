"""
Local Search & Scraping Client
Drop-in replacement for Tavily and Firecrawl clients
"""

import asyncio
import httpx
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

class LocalSearchClient:
    """
    Drop-in replacement for Tavily search client
    """
    
    def __init__(self, base_url: str = "http://localhost:8082"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str = "basic",
        include_answer: bool = False,
        include_raw_content: bool = False,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search using local SearXNG instance
        Compatible with Tavily API
        """
        request_data = {
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
            "include_domains": include_domains,
            "exclude_domains": exclude_domains
        }
        
        response = await self.client.post(
            urljoin(self.base_url, "/search"),
            json=request_data
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

class LocalScrapingClient:
    """
    Drop-in replacement for Firecrawl client
    """
    
    def __init__(self, base_url: str = "http://localhost:8082"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def scrape_url(
        self,
        url: str,
        formats: List[str] = ["markdown", "html"],
        include_tags: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None,
        only_main_content: bool = True,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Scrape a single URL
        Compatible with Firecrawl API
        """
        request_data = {
            "url": url,
            "formats": formats,
            "include_tags": include_tags,
            "exclude_tags": exclude_tags,
            "only_main_content": only_main_content,
            "timeout": timeout
        }
        
        response = await self.client.post(
            urljoin(self.base_url, "/scrape"),
            json=request_data
        )
        response.raise_for_status()
        return response.json()
    
    async def batch_scrape(self, urls: List[str]) -> Dict[str, Any]:
        """
        Scrape multiple URLs in batch
        """
        response = await self.client.post(
            urljoin(self.base_url, "/batch-scrape"),
            json=urls
        )
        response.raise_for_status()
        return response.json()
    
    async def get_batch_results(self, job_id: str) -> Dict[str, Any]:
        """
        Get results from batch scraping job
        """
        response = await self.client.get(
            urljoin(self.base_url, f"/batch-scrape/{job_id}")
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

# Compatibility functions for existing code
async def tavily_search(query: str, **kwargs) -> Dict[str, Any]:
    """
    Compatibility function for existing Tavily search calls
    """
    client = LocalSearchClient()
    try:
        return await client.search(query, **kwargs)
    finally:
        await client.close()

async def firecrawl_scrape(url: str, **kwargs) -> Dict[str, Any]:
    """
    Compatibility function for existing Firecrawl scrape calls
    """
    client = LocalScrapingClient()
    try:
        return await client.scrape_url(url, **kwargs)
    finally:
        await client.close()

# Example usage
async def main():
    """Example usage of the local search and scraping services"""
    
    # Search example
    search_client = LocalSearchClient()
    search_results = await search_client.search(
        query="Python web scraping best practices",
        max_results=5
    )
    print("Search Results:")
    for result in search_results["results"]:
        print(f"- {result['title']}: {result['url']}")
    
    # Scraping example
    scraping_client = LocalScrapingClient()
    if search_results["results"]:
        first_url = search_results["results"][0]["url"]
        scrape_result = await scraping_client.scrape_url(
            url=first_url,
            formats=["markdown", "text"]
        )
        print(f"\nScraped content from {first_url}:")
        print(f"Title: {scrape_result['metadata']['title']}")
        print(f"Content length: {len(scrape_result.get('markdown', ''))}")
    
    # Clean up
    await search_client.close()
    await scraping_client.close()

if __name__ == "__main__":
    asyncio.run(main())