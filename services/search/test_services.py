#!/usr/bin/env python3
"""
Test script for local search and scraping services
"""

import asyncio
import json
import httpx

BASE_URL = "http://localhost:8082"

async def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print(f"✅ Health check: {response.json()}")

async def test_search():
    """Test search functionality"""
    print("\n🔍 Testing search functionality...")
    
    search_data = {
        "query": "Python web scraping best practices",
        "max_results": 5
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/search",
            json=search_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Search completed in {result['response_time']:.2f}s")
            print(f"📊 Found {len(result['results'])} results for: {result['query']}")
            
            for i, item in enumerate(result['results'], 1):
                print(f"  {i}. {item['title'][:80]}...")
                print(f"     URL: {item['url']}")
                print(f"     Content: {item['content'][:100]}...")
                print()
        else:
            print(f"❌ Search failed: {response.status_code} - {response.text}")

async def test_scrape():
    """Test scraping functionality"""
    print("🔍 Testing scraping functionality...")
    
    scrape_data = {
        "url": "https://httpbin.org/html",
        "formats": ["text", "markdown"]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/scrape",
            json=scrape_data
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print(f"✅ Scraping successful for: {result['url']}")
                print(f"📄 Title: {result['metadata'].get('title', 'No title')}")
                print(f"📝 Content length: {len(result.get('text', ''))}")
                print(f"🔤 First 200 chars: {result.get('text', '')[:200]}...")
            else:
                print(f"❌ Scraping failed: {result['metadata'].get('error', 'Unknown error')}")
        else:
            print(f"❌ Scrape request failed: {response.status_code} - {response.text}")

async def test_scrape_real_website():
    """Test scraping a real website"""
    print("\n🔍 Testing scraping real website...")
    
    scrape_data = {
        "url": "https://example.com",
        "formats": ["text"]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/scrape",
            json=scrape_data
        )
        
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print(f"✅ Real website scraping successful for: {result['url']}")
                print(f"📄 Title: {result['metadata'].get('title', 'No title')}")
                print(f"📝 Content length: {len(result.get('text', ''))}")
                print(f"🔤 First 200 chars: {result.get('text', '')[:200]}...")
            else:
                print(f"❌ Real website scraping failed: {result['metadata'].get('error', 'Unknown error')}")
        else:
            print(f"❌ Real website scrape request failed: {response.status_code} - {response.text}")

async def main():
    """Run all tests"""
    print("🚀 Starting Local Search & Scraping Service Tests")
    print("=" * 60)
    
    try:
        await test_health()
        await test_search()
        await test_scrape()
        await test_scrape_real_website()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("\n📋 Service Summary:")
        print(f"   • Health endpoint: {BASE_URL}/health")
        print(f"   • Search API: {BASE_URL}/search")
        print(f"   • Scraping API: {BASE_URL}/scrape")
        print(f"   • API Documentation: {BASE_URL}/docs")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(main())