"""
Local Web Scraping Service
Provides Tavily and Firecrawl-compatible APIs for web search and scraping
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
import structlog
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from fastapi import FastAPI, HTTPException, BackgroundTasks
from playwright.async_api import async_playwright, Browser, BrowserContext
from pydantic import BaseModel, HttpUrl
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8080")
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))

# Initialize FastAPI app
app = FastAPI(
    title="Suna Local Search & Scraping Service",
    description="Local replacement for Tavily and Firecrawl services",
    version="1.0.0"
)

# Global variables
redis_client: Optional[redis.Redis] = None
browser: Optional[Browser] = None
user_agent = UserAgent()

# Simple throttling
request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

# Pydantic models
class SearchRequest(BaseModel):
    query: str
    max_results: int = 10
    search_depth: str = "basic"  # basic, advanced
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
    screenshot: Optional[str] = None

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    global redis_client, browser
    
    # Initialize Redis connection
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    await redis_client.ping()
    logger.info("Connected to Redis")
    
    # Initialize Playwright browser
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-first-run",
            "--no-zygote",
            "--disable-gpu"
        ]
    )
    logger.info("Playwright browser initialized")

@app.on_event("shutdown")
async def shutdown_event():
    global redis_client, browser
    
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")
    
    if browser:
        await browser.close()
        logger.info("Playwright browser closed")

# Utility functions
def generate_cache_key(prefix: str, data: str) -> str:
    """Generate a cache key from data"""
    hash_obj = hashlib.md5(data.encode())
    return f"{prefix}:{hash_obj.hexdigest()}"

async def get_cached_result(key: str) -> Optional[Dict]:
    """Get cached result from Redis"""
    try:
        cached = await redis_client.get(key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning("Cache get error", error=str(e))
    return None

async def set_cached_result(key: str, data: Dict, ttl: int = CACHE_TTL):
    """Set cached result in Redis"""
    try:
        await redis_client.setex(key, ttl, json.dumps(data))
    except Exception as e:
        logger.warning("Cache set error", error=str(e))

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def search_with_searxng(query: str, num_results: int = 10) -> List[Dict]:
    """Search using SearXNG"""
    async with request_semaphore:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            try:
                response = await client.post(
                    f"{SEARXNG_URL}/search",
                    data={
                        "q": query,
                        "format": "json",
                        "engines": "google,bing,duckduckgo",
                        "safesearch": "0"
                    },
                    headers={
                        "User-Agent": user_agent.random,
                        "Accept": "application/json"
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                results = []
                
                for result in data.get("results", [])[:num_results]:
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": result.get("content", ""),
                        "score": 1.0,  # SearXNG doesn't provide scores
                        "published_date": result.get("publishedDate")
                    })
                
                return results
                
            except Exception as e:
                logger.error("SearXNG search error", error=str(e), query=query)
                raise

async def scrape_with_playwright(url: str, context: BrowserContext) -> Dict[str, Any]:
    """Scrape a URL using Playwright"""
    page = await context.new_page()
    
    try:
        # Navigate to the page
        await page.goto(url, wait_until="domcontentloaded", timeout=REQUEST_TIMEOUT * 1000)
        
        # Wait for any dynamic content
        await page.wait_for_timeout(2000)
        
        # Get page content
        html_content = await page.content()
        text_content = await page.evaluate("document.body.innerText")
        
        # Extract metadata
        title = await page.title()
        
        # Get meta description
        description_element = await page.query_selector('meta[name="description"]')
        description = ""
        if description_element:
            description = await description_element.get_attribute("content") or ""
        
        # Extract main content using BeautifulSoup (simple extraction)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        main_content = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in main_content.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        main_content = ' '.join(chunk for chunk in chunks if chunk)
        
        return {
            "html": html_content,
            "text": text_content,
            "main_content": main_content or text_content,
            "title": title,
            "description": description,
            "url": url
        }
        
    except Exception as e:
        logger.error("Playwright scraping error", error=str(e), url=url)
        raise
    finally:
        await page.close()

# API endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        await redis_client.ping()
        return {"status": "healthy", "timestamp": time.time()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    """
    Search endpoint compatible with Tavily API
    """
    start_time = time.time()
    
    # Generate cache key
    cache_key = generate_cache_key("search", f"{request.query}:{request.max_results}")
    
    # Check cache first
    cached_result = await get_cached_result(cache_key)
    if cached_result:
        logger.info("Returning cached search result", query=request.query)
        return SearchResponse(**cached_result)
    
    try:
        # Perform search
        search_results = await search_with_searxng(request.query, request.max_results)
        
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
        
        logger.info("Search completed", query=request.query, results_count=len(results))
        return response
        
    except Exception as e:
        logger.error("Search error", error=str(e), query=request.query)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/scrape", response_model=ScrapeResult)
async def scrape(request: ScrapeRequest) -> ScrapeResult:
    """
    Scrape endpoint compatible with Firecrawl API
    """
    url = str(request.url)
    
    # Generate cache key
    cache_key = generate_cache_key("scrape", url)
    
    # Check cache first
    cached_result = await get_cached_result(cache_key)
    if cached_result:
        logger.info("Returning cached scrape result", url=url)
        return ScrapeResult(**cached_result)
    
    try:
        # Create browser context with random user agent
        context = await browser.new_context(
            user_agent=user_agent.random,
            viewport={"width": 1920, "height": 1080}
        )
        
        # Scrape the URL
        scraped_data = await scrape_with_playwright(url, context)
        await context.close()
        
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
        
        if "markdown" in request.formats:
            # Convert main content to markdown-like format
            result_data["markdown"] = scraped_data["main_content"]
        
        if "text" in request.formats:
            result_data["text"] = scraped_data["text"]
        
        result = ScrapeResult(**result_data)
        
        # Cache the result
        await set_cached_result(cache_key, result.dict())
        
        logger.info("Scrape completed", url=url)
        return result
        
    except Exception as e:
        logger.error("Scrape error", error=str(e), url=url)
        return ScrapeResult(
            success=False,
            url=url,
            metadata={"error": str(e)}
        )

@app.post("/batch-scrape")
async def batch_scrape(urls: List[HttpUrl], background_tasks: BackgroundTasks):
    """
    Batch scrape multiple URLs
    """
    job_id = hashlib.md5(f"{time.time()}:{len(urls)}".encode()).hexdigest()
    
    async def process_batch():
        results = []
        context = await browser.new_context(
            user_agent=user_agent.random,
            viewport={"width": 1920, "height": 1080}
        )
        
        try:
            for url in urls:
                try:
                    scraped_data = await scrape_with_playwright(str(url), context)
                    results.append({
                        "url": str(url),
                        "success": True,
                        "data": scraped_data
                    })
                except Exception as e:
                    results.append({
                        "url": str(url),
                        "success": False,
                        "error": str(e)
                    })
            
            # Store results in cache
            await set_cached_result(f"batch:{job_id}", {"results": results}, ttl=7200)
            
        finally:
            await context.close()
    
    background_tasks.add_task(process_batch)
    
    return {"job_id": job_id, "status": "processing", "urls_count": len(urls)}

@app.get("/batch-scrape/{job_id}")
async def get_batch_results(job_id: str):
    """
    Get batch scrape results
    """
    results = await get_cached_result(f"batch:{job_id}")
    if not results:
        raise HTTPException(status_code=404, detail="Job not found or expired")
    
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)