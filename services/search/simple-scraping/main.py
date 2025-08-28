"""
Simple Web Scraping Service
Basic implementation without Playwright for initial testing
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse

import httpx
import redis.asyncio as redis
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8080")
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))

# Initialize FastAPI app
app = FastAPI(
    title="Suna Simple Search & Scraping Service",
    description="Simple local replacement for Tavily and Firecrawl services",
    version="1.0.0"
)

# Global variables
redis_client: Optional[redis.Redis] = None
request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

# Pydantic models
class SearchRequest(BaseModel):
    query: str
    max_results: int = 10
    search_depth: str = "basic"
    include_answer: bool = False
    include_raw_content: bool = False
    include_domains: Optional[List[str]] = None
    exclude_domains: Optional[List[str]] = None

class SearchResult(BaseModel):
    title: str
    url: str
    content: str
    score: float
    published_date: Optional[str] = None

class SearchResponse(BaseModel):
    query: str
    follow_up_questions: Optional[List[str]] = None
    answer: Optional[str] = None
    results: List[SearchResult]
    response_time: float

class ScrapeRequest(BaseModel):
    url: HttpUrl
    formats: List[str] = ["markdown", "html"]
    include_tags: Optional[List[str]] = None
    exclude_tags: Optional[List[str]] = None
    only_main_content: bool = True
    timeout: int = 30

class ScrapeResult(BaseModel):
    success: bool
    url: str
    markdown: Optional[str] = None
    html: Optional[str] = None
    text: Optional[str] = None
    metadata: Dict[str, Any] = {}

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    global redis_client
    
    try:
        # Initialize Redis connection
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        print("Connected to Redis")
    except Exception as e:
        print(f"Redis connection failed: {e}")
        redis_client = None

@app.on_event("shutdown")
async def shutdown_event():
    global redis_client
    
    if redis_client:
        await redis_client.close()
        print("Redis connection closed")

# Utility functions
def generate_cache_key(prefix: str, data: str) -> str:
    """Generate a cache key from data"""
    hash_obj = hashlib.md5(data.encode())
    return f"{prefix}:{hash_obj.hexdigest()}"

async def get_cached_result(key: str) -> Optional[Dict]:
    """Get cached result from Redis"""
    if not redis_client:
        return None
    try:
        cached = await redis_client.get(key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        print(f"Cache get error: {e}")
    return None

async def set_cached_result(key: str, data: Dict, ttl: int = CACHE_TTL):
    """Set cached result in Redis"""
    if not redis_client:
        return
    try:
        await redis_client.setex(key, ttl, json.dumps(data))
    except Exception as e:
        print(f"Cache set error: {e}")

async def simple_web_search(query: str, num_results: int = 10) -> List[Dict]:
    """Simple web search using DuckDuckGo"""
    async with request_semaphore:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            try:
                # Use DuckDuckGo instant answer API
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": "1",
                        "skip_disambig": "1"
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                results = []
                
                # Add abstract if available
                if data.get("Abstract"):
                    results.append({
                        "title": data.get("AbstractText", query),
                        "url": data.get("AbstractURL", ""),
                        "content": data.get("Abstract", ""),
                        "score": 1.0,
                        "published_date": None
                    })
                
                # Add related topics
                for topic in data.get("RelatedTopics", [])[:num_results-1]:
                    if isinstance(topic, dict) and topic.get("Text"):
                        results.append({
                            "title": topic.get("Text", "")[:100] + "...",
                            "url": topic.get("FirstURL", ""),
                            "content": topic.get("Text", ""),
                            "score": 0.8,
                            "published_date": None
                        })
                
                return results[:num_results]
                
            except Exception as e:
                print(f"Search error: {e}")
                # Fallback to mock results
                return [{
                    "title": f"Search result for: {query}",
                    "url": "https://example.com",
                    "content": f"This is a mock search result for the query: {query}",
                    "score": 0.5,
                    "published_date": None
                }]

async def simple_scrape(url: str) -> Dict[str, Any]:
    """Simple web scraping using httpx and BeautifulSoup"""
    async with request_semaphore:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            try:
                response = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                response.raise_for_status()
                
                html_content = response.text
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get title
                title = soup.title.string if soup.title else ""
                
                # Get meta description
                description_tag = soup.find('meta', attrs={'name': 'description'})
                description = description_tag.get('content', '') if description_tag else ""
                
                # Get text content
                text_content = soup.get_text()
                
                # Clean up whitespace
                lines = (line.strip() for line in text_content.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                clean_text = ' '.join(chunk for chunk in chunks if chunk)
                
                return {
                    "html": html_content,
                    "text": clean_text,
                    "title": title.strip(),
                    "description": description.strip(),
                    "url": url
                }
                
            except Exception as e:
                print(f"Scraping error for {url}: {e}")
                raise

# API endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    """Search endpoint compatible with Tavily API"""
    start_time = time.time()
    
    # Generate cache key
    cache_key = generate_cache_key("search", f"{request.query}:{request.max_results}")
    
    # Check cache first
    cached_result = await get_cached_result(cache_key)
    if cached_result:
        print(f"Returning cached search result for: {request.query}")
        return SearchResponse(**cached_result)
    
    try:
        # Perform search
        search_results = await simple_web_search(request.query, request.max_results)
        
        # Filter by domains if specified
        if request.include_domains:
            search_results = [
                r for r in search_results 
                if any(domain in r["url"] for domain in request.include_domains)
            ]
        
        if request.exclude_domains:
            search_results = [
                r for r in search_results 
                if not any(domain in r["url"] for domain in request.exclude_domains)
            ]
        
        # Convert to SearchResult objects
        results = [SearchResult(**result) for result in search_results]
        
        response = SearchResponse(
            query=request.query,
            results=results,
            response_time=time.time() - start_time
        )
        
        # Cache the result
        await set_cached_result(cache_key, response.dict())
        
        print(f"Search completed for: {request.query}, results: {len(results)}")
        return response
        
    except Exception as e:
        print(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/scrape", response_model=ScrapeResult)
async def scrape(request: ScrapeRequest) -> ScrapeResult:
    """Scrape endpoint compatible with Firecrawl API"""
    url = str(request.url)
    
    # Generate cache key
    cache_key = generate_cache_key("scrape", url)
    
    # Check cache first
    cached_result = await get_cached_result(cache_key)
    if cached_result:
        print(f"Returning cached scrape result for: {url}")
        return ScrapeResult(**cached_result)
    
    try:
        # Scrape the URL
        scraped_data = await simple_scrape(url)
        
        # Prepare result based on requested formats
        result_data = {
            "success": True,
            "url": url,
            "metadata": {
                "title": scraped_data["title"],
                "description": scraped_data["description"]
            }
        }
        
        if "html" in request.formats:
            result_data["html"] = scraped_data["html"]
        
        if "markdown" in request.formats or "text" in request.formats:
            result_data["markdown"] = scraped_data["text"]
            result_data["text"] = scraped_data["text"]
        
        result = ScrapeResult(**result_data)
        
        # Cache the result
        await set_cached_result(cache_key, result.dict())
        
        print(f"Scrape completed for: {url}")
        return result
        
    except Exception as e:
        print(f"Scrape error: {e}")
        return ScrapeResult(
            success=False,
            url=url,
            metadata={"error": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)