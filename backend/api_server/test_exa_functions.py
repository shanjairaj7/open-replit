#!/usr/bin/env python3
"""
Test Exa.ai functions to verify they work and document response structures
"""

import os
import json
from exa_py import Exa
from dotenv import load_dotenv

load_dotenv()

# Initialize Exa client (use hardcoded key for testing)
exa = Exa(api_key="16fe8779-7264-44c1-a911-e8187cb629c6")

def basic_search(query: str):
    """Perform basic Exa search"""
    print(f"==> Testing basic_search with query: '{query}'")
    
    if not query:
        return {"error": "Query is required"}
    
    try:
        # Basic search - returns up to 10 results by default
        results = exa.search(
            query,
            num_results=3,  # Smaller for testing
            use_autoprompt=True  # Automatically optimizes the query
        )
        
        print(f"   Raw result type: {type(results)}")
        print(f"   Has results attr: {hasattr(results, 'results')}")
        
        if hasattr(results, 'results'):
            print(f"   Number of results: {len(results.results)}")
        
        # Format results
        formatted_results = []
        for result in results.results:
            print(f"   Result attrs: {dir(result)}")
            formatted_results.append({
                "title": result.title,
                "url": result.url,
                "score": result.score,
                "published_date": result.published_date,
                "author": result.author if hasattr(result, 'author') else None
            })
        
        return {
            "success": True,
            "results": formatted_results,
            "query": query,
            "total_results": len(formatted_results)
        }
    except Exception as e:
        print(f"   Error: {e}")
        return {"error": f"Search failed: {str(e)}"}

def search_with_content(query: str, max_chars: int = 500):
    """Search and extract page content"""
    print(f"==> Testing search_with_content with query: '{query}'")
    
    if not query:
        return {"error": "Query is required"}
    
    try:
        # Search and get contents in one call
        results = exa.search_and_contents(
            query,
            num_results=2,  # Smaller for testing
            text={
                "include_html_tags": False,  # Clean text only
                "max_characters": max_chars  # Limit content length
            },
            highlights={
                "highlights_per_url": 2,  # Get key excerpts
                "num_sentences": 1
            }
        )
        
        print(f"   Raw result type: {type(results)}")
        print(f"   Number of results: {len(results.results)}")
        
        formatted_results = []
        for result in results.results:
            print(f"   Content result attrs: {dir(result)}")
            formatted_results.append({
                "title": result.title,
                "url": result.url,
                "text": result.text if hasattr(result, 'text') else "",
                "highlights": result.highlights if hasattr(result, 'highlights') else [],
                "summary": result.summary if hasattr(result, 'summary') else ""
            })
        
        return {
            "success": True,
            "results": formatted_results,
            "query": query
        }
    except Exception as e:
        print(f"   Error: {e}")
        return {"error": f"Search failed: {str(e)}"}

def advanced_search(query: str, filters: dict = None):
    """Advanced search with filtering options"""
    print(f"==> Testing advanced_search with query: '{query}' and filters: {filters}")
    
    if not query:
        return {"error": "Query is required"}
    
    filters = filters or {}
    
    # Optional filters
    start_date = filters.get("start_date")  # Format: "2024-01-01"
    end_date = filters.get("end_date")
    include_domains = filters.get("include_domains", [])  # ["example.com", "docs.com"]
    exclude_domains = filters.get("exclude_domains", [])
    category = filters.get("category")  # "news", "blog", "company", etc.
    
    try:
        # Build search parameters
        search_params = {
            "query": query,
            "num_results": 2,  # Smaller for testing
            "use_autoprompt": True
        }
        
        # Add date filters if provided
        if start_date:
            search_params["start_published_date"] = start_date
        if end_date:
            search_params["end_published_date"] = end_date
            
        # Add domain filters
        if include_domains:
            search_params["include_domains"] = include_domains
        if exclude_domains:
            search_params["exclude_domains"] = exclude_domains
            
        # Add category filter
        if category:
            search_params["category"] = category
        
        print(f"   Search params: {search_params}")
        
        results = exa.search(**search_params)
        
        formatted_results = []
        for result in results.results:
            formatted_results.append({
                "title": result.title,
                "url": result.url,
                "score": result.score,
                "published_date": result.published_date
            })
        
        return {
            "success": True,
            "results": formatted_results,
            "filters_applied": {
                "date_range": f"{start_date or 'any'} to {end_date or 'any'}",
                "domains": include_domains or "all",
                "excluded": exclude_domains or "none",
                "category": category or "all"
            }
        }
    except Exception as e:
        print(f"   Error: {e}")
        return {"error": f"Advanced search failed: {str(e)}"}

def find_similar_pages(url: str):
    """Find pages similar to a given URL"""
    print(f"==> Testing find_similar_pages with URL: '{url}'")
    
    if not url:
        return {"error": "URL is required"}
    
    try:
        # Find similar pages
        results = exa.find_similar(
            url,
            num_results=2,  # Smaller for testing
            exclude_source_domain=True  # Don't include same website
        )
        
        formatted_results = []
        for result in results.results:
            formatted_results.append({
                "title": result.title,
                "url": result.url,
                "score": result.score,
                "similarity": "high" if result.score > 0.8 else "medium"
            })
        
        return {
            "success": True,
            "source_url": url,
            "similar_pages": formatted_results
        }
    except Exception as e:
        print(f"   Error: {e}")
        return {"error": f"Similar search failed: {str(e)}"}

def main():
    """Test all Exa.ai functions"""
    print("🔍 Testing Exa.ai Functions")
    print("=" * 50)
    
    # Test 1: Basic search
    print("\n1. BASIC SEARCH TEST")
    basic_result = basic_search("Python programming language")
    print(f"Basic search result structure:")
    print(json.dumps(basic_result, indent=2))
    
    # Test 2: Search with content
    print("\n2. SEARCH WITH CONTENT TEST")
    content_result = search_with_content("machine learning tutorials")
    print(f"Content search result structure:")
    print(json.dumps(content_result, indent=2))
    
    # Test 3: Advanced search with filters
    print("\n3. ADVANCED SEARCH TEST")
    filters = {
        "start_date": "2024-01-01",
        "include_domains": ["github.com"]
    }
    advanced_result = advanced_search("React components", filters)
    print(f"Advanced search result structure:")
    print(json.dumps(advanced_result, indent=2))
    
    # Test 4: Find similar pages
    print("\n4. FIND SIMILAR PAGES TEST")
    similar_result = find_similar_pages("https://docs.python.org/3/")
    print(f"Similar pages result structure:")
    print(json.dumps(similar_result, indent=2))
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main()