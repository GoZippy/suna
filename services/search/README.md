# Local Search & Scraping Services

This directory contains local replacements for Tavily (search) and Firecrawl (web scraping) services, providing self-hosted alternatives that eliminate external API dependencies.

## Services Overview

### 1. SearXNG (Metasearch Engine)
- **Purpose**: Aggregates results from multiple search engines
- **Port**: 8080
- **Features**: Privacy-focused, no tracking, multiple search engines
- **Web UI**: http://localhost:8080

### 2. Redis (Caching Layer)
- **Purpose**: Caches search results and scraping data
- **Port**: 6380
- **Features**: Fast in-memory caching, configurable TTL

### 3. Web Scraping Service
- **Purpose**: Extracts content from web pages using Playwright
- **Port**: 8081
- **Features**: JavaScript rendering, multiple output formats, rate limiting
- **API Docs**: http://localhost:8081/docs

## Quick Start

### Windows (PowerShell)
```powershell
.\start.ps1
```

### Linux/macOS (Bash)
```bash
chmod +x start.sh
./start.sh
```

### Manual Start
```bash
docker-compose up -d
```

## API Usage

### Search API (Tavily Compatible)

```python
import asyncio
from client import LocalSearchClient

async def search_example():
    client = LocalSearchClient()
    
    results = await client.search(
        query="Python web scraping",
        max_results=5,
        include_domains=["github.com", "stackoverflow.com"]
    )
    
    for result in results["results"]:
        print(f"{result['title']}: {result['url']}")
    
    await client.close()

asyncio.run(search_example())
```

### Scraping API (Firecrawl Compatible)

```python
import asyncio
from client import LocalScrapingClient

async def scrape_example():
    client = LocalScrapingClient()
    
    result = await client.scrape_url(
        url="https://example.com",
        formats=["markdown", "text"],
        only_main_content=True
    )
    
    print(f"Title: {result['metadata']['title']}")
    print(f"Content: {result['markdown'][:500]}...")
    
    await client.close()

asyncio.run(scrape_example())
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `SEARXNG_URL` | `http://localhost:8080` | SearXNG instance URL |
| `MAX_CONCURRENT_REQUESTS` | `10` | Maximum concurrent scraping requests |
| `REQUEST_TIMEOUT` | `30` | Request timeout in seconds |
| `CACHE_TTL` | `3600` | Cache time-to-live in seconds |

### SearXNG Configuration

Edit `searxng/settings.yml` to:
- Enable/disable search engines
- Configure rate limiting
- Set up proxy rotation
- Customize search behavior

### Redis Configuration

Edit `redis/redis.conf` to:
- Adjust memory limits
- Configure persistence
- Set up authentication

## API Endpoints

### Search Service

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/search` | POST | Search using SearXNG |
| `/health` | GET | Health check |

### Scraping Service

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/scrape` | POST | Scrape a single URL |
| `/batch-scrape` | POST | Start batch scraping job |
| `/batch-scrape/{job_id}` | GET | Get batch results |
| `/health` | GET | Health check |

## Integration with Existing Code

### Replace Tavily Client

```python
# Before (Tavily)
from tavily import TavilyClient
client = TavilyClient(api_key="your-key")
results = client.search("query")

# After (Local)
from services.search.client import LocalSearchClient
client = LocalSearchClient()
results = await client.search("query")
```

### Replace Firecrawl Client

```python
# Before (Firecrawl)
from firecrawl import FirecrawlApp
app = FirecrawlApp(api_key="your-key")
result = app.scrape_url("https://example.com")

# After (Local)
from services.search.client import LocalScrapingClient
client = LocalScrapingClient()
result = await client.scrape_url("https://example.com")
```

## Performance Tuning

### SearXNG Optimization
- Enable result caching
- Configure rate limiting per IP
- Use multiple search engines for better results
- Set up proxy rotation for high-volume usage

### Scraping Service Optimization
- Adjust `MAX_CONCURRENT_REQUESTS` based on your system
- Increase `CACHE_TTL` for frequently accessed content
- Use batch scraping for multiple URLs
- Configure Playwright browser pool size

### Redis Optimization
- Set appropriate `maxmemory` limit
- Use `allkeys-lru` eviction policy for caching
- Monitor memory usage and hit rates
- Consider Redis clustering for high load

## Monitoring

### Health Checks
```bash
# Check all services
curl http://localhost:8080/healthz  # SearXNG
curl http://localhost:8081/health   # Scraping Service
docker exec suna_search_redis redis-cli ping  # Redis
```

### Logs
```bash
# View service logs
docker-compose logs -f searxng
docker-compose logs -f scraping-service
docker-compose logs -f redis
```

### Metrics
- SearXNG: Built-in statistics at `/stats`
- Redis: Use `redis-cli info` for metrics
- Scraping Service: Custom metrics in logs

## Troubleshooting

### Common Issues

1. **SearXNG not returning results**
   - Check if search engines are blocked
   - Verify network connectivity
   - Review rate limiting settings

2. **Scraping timeouts**
   - Increase `REQUEST_TIMEOUT`
   - Check target website's response time
   - Verify Playwright browser is running

3. **High memory usage**
   - Reduce Redis cache size
   - Lower `CACHE_TTL`
   - Limit concurrent requests

4. **Port conflicts**
   - Change ports in `docker-compose.yml`
   - Update client configuration
   - Check for other services using same ports

### Debug Mode

Enable debug logging:
```bash
# Set environment variable
export DEBUG=1

# Or modify docker-compose.yml
environment:
  - DEBUG=1
```

## Security Considerations

### Network Security
- Run services behind a reverse proxy
- Use HTTPS for external access
- Implement IP whitelisting if needed

### Rate Limiting
- Configure per-IP limits in SearXNG
- Implement application-level throttling
- Monitor for abuse patterns

### Data Privacy
- SearXNG doesn't log search queries by default
- Scraped content is cached temporarily
- Consider data retention policies

## Scaling

### Horizontal Scaling
- Run multiple scraping service instances
- Use Redis Cluster for distributed caching
- Load balance requests across instances

### Vertical Scaling
- Increase container resource limits
- Add more CPU cores for Playwright
- Increase memory for Redis caching

## Backup and Recovery

### Data Backup
```bash
# Backup Redis data
docker exec suna_search_redis redis-cli BGSAVE

# Backup configuration
tar -czf search-config-backup.tar.gz searxng/ redis/ scraping/
```

### Recovery
```bash
# Restore configuration
tar -xzf search-config-backup.tar.gz

# Restart services
docker-compose down && docker-compose up -d
```