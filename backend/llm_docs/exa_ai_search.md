# Exa.ai Integration Guide - Web Search API

## Quick Setup

**Requirements:** Add to `requirements.txt`:
```
exa-py==1.15.4
python-dotenv
```

**IMPORTANT:** You must use `exa-py>=1.15.4`. Older versions like 1.0.7 will cause errors with direct attribute access to `image`, `favicon`, and other newer fields.

**Environment:** The `EXA_API_KEY` is automatically provided in all deployed backends.

**Basic Client Setup:**
```python
from exa_py import Exa
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Exa client
exa = Exa(api_key=os.getenv("EXA_API_KEY"))
```

## Core Search Methods

### 1. Basic Search
Simple search that returns URLs and metadata:
```python
def basic_search(query: str):
    """Perform basic Exa search"""
    if not query:
        return {"error": "Query is required"}
    
    try:
        results = exa.search(
            query,
            num_results=10,
            use_autoprompt=True
        )
        
        formatted_results = []
        for result in results.results:
            formatted_results.append({
                "title": result.title,
                "url": result.url,
                "score": result.score,
                "published_date": result.published_date,
                "author": result.author,
                "image": result.image,
                "favicon": result.favicon
            })
        
        return {
            "success": True,
            "results": formatted_results,
            "query": query,
            "total_results": len(formatted_results)
        }
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}
```

**Example Response:**
```json
{
  "success": true,
  "results": [
    {
      "title": "Python Documentation contents",
      "url": "https://docs.python.org/3/contents.html",
      "score": null,
      "published_date": "2025-09-01T18:07:00.000Z",
      "author": "",
      "image": null,
      "favicon": "https://docs.python.org/favicon.ico"
    },
    {
      "title": "Python (programming language) - Wikipedia", 
      "url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
      "score": null,
      "published_date": null,
      "author": null,
      "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/1200px-Python-logo-notext.svg.png",
      "favicon": "https://en.wikipedia.org/favicon.ico"
    }
  ],
  "query": "Python programming language", 
  "total_results": 2
}
```

### 2. Search with Content Extraction
Get search results with actual page content:
```python
def search_with_content(query: str, max_chars: int = 1000):
    """Search and extract page content"""
    if not query:
        return {"error": "Query is required"}
    
    try:
        results = exa.search_and_contents(
            query,
            num_results=5,
            text={
                "include_html_tags": False,
                "max_characters": max_chars
            },
            highlights={
                "highlights_per_url": 3,
                "num_sentences": 2
            }
        )
        
        formatted_results = []
        for result in results.results:
            formatted_results.append({
                "title": result.title,
                "url": result.url,
                "text": result.text,
                "highlights": result.highlights,
                "summary": result.summary,
                "image": result.image,
                "favicon": result.favicon
            })
        
        return {
            "success": True,
            "results": formatted_results,
            "query": query
        }
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}
```

**Example Response:**
```json
{
  "success": true,
  "results": [
    {
      "title": "Machine Learning Crash Course - Google for Developers",
      "url": "https://developers.google.com/machine-learning/crash-course",
      "text": "[Skip to main content](https://developers.google.com/developers.google.com#main-content)\n\n- [**Machine Learning**](https://developers.google.com/machine-learning)\n\n`/`\n\n- English\n- Deutsch\n- Español...",
      "highlights": [
        "Since 2018, millions of people worldwide have relied on Machine Learning Crash Course to learn how machine learning works.",
        "Watch this video to learn more about the new-and-improved MLCC."
      ],
      "summary": null,
      "image": null,
      "favicon": "https://developers.google.com/favicon.ico"
    }
  ],
  "query": "machine learning tutorials"
}
```

### 3. Advanced Search with Filters
Search with date ranges, domain filters, and categories:
```python
def advanced_search(query: str, filters: dict = None):
    """Advanced search with filtering options"""
    if not query:
        return {"error": "Query is required"}
    
    filters = filters or {}
    start_date = filters.get("start_date")
    end_date = filters.get("end_date") 
    include_domains = filters.get("include_domains", [])
    exclude_domains = filters.get("exclude_domains", [])
    category = filters.get("category")
    
    try:
        search_params = {
            "query": query,
            "num_results": 10,
            "use_autoprompt": True
        }
        
        if start_date:
            search_params["start_published_date"] = start_date
        if end_date:
            search_params["end_published_date"] = end_date
        if include_domains:
            search_params["include_domains"] = include_domains
        if exclude_domains:
            search_params["exclude_domains"] = exclude_domains
        if category:
            search_params["category"] = category
        
        results = exa.search(**search_params)
        
        formatted_results = []
        for result in results.results:
            formatted_results.append({
                "title": result.title,
                "url": result.url,
                "score": result.score,
                "published_date": result.published_date,
                "author": result.author,
                "image": result.image,
                "favicon": result.favicon
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
        return {"error": f"Advanced search failed: {str(e)}"}
```

**Example Response:**
```json
{
  "success": true,
  "results": [
    {
      "title": "facebook/react: The library for web and native user interfaces. - GitHub",
      "url": "https://github.com/facebook/react",
      "score": null,
      "published_date": "2025-07-28T12:00:00.000Z",
      "author": null,
      "image": null,
      "favicon": "https://github.com/favicon.ico"
    },
    {
      "title": "Official React components built for Flowbite and Tailwind CSS - GitHub", 
      "url": "https://github.com/themesberg/flowbite-react",
      "score": null,
      "published_date": "2025-03-24T12:00:00.000Z",
      "author": null,
      "image": null,
      "favicon": "https://github.com/favicon.ico"
    }
  ],
  "filters_applied": {
    "date_range": "2024-01-01 to any",
    "domains": ["github.com"],
    "excluded": "none", 
    "category": "all"
  }
}
```

### 4. Find Similar Content
Find pages similar to a given URL:
```python
def find_similar_pages(url: str):
    """Find pages similar to a given URL"""
    if not url:
        return {"error": "URL is required"}
    
    try:
        results = exa.find_similar(
            url,
            num_results=10,
            exclude_source_domain=True
        )
        
        formatted_results = []
        for result in results.results:
            formatted_results.append({
                "title": result.title,
                "url": result.url,
                "score": result.score,
                "similarity": "high" if result.score > 0.8 else "medium",
                "image": result.image,
                "favicon": result.favicon
            })
        
        return {
            "success": True,
            "source_url": url,
            "similar_pages": formatted_results
        }
    except Exception as e:
        return {"error": f"Similar search failed: {str(e)}"}
```

**Example Response:**
```json
{
  "success": true,
  "source_url": "https://docs.python.org/3/",
  "similar_pages": [
    {
      "title": "Python 2.5.2 Documentation",
      "url": "https://www.python.org/doc/2.5.2/",
      "score": 0.9068735837936401,
      "similarity": "high",
      "image": null,
      "favicon": "https://www.python.org/favicon.ico"
    },
    {
      "title": "3.7.0a2 Documentation",
      "url": "https://python.readthedocs.io/en/latest/",
      "score": 0.9043111801147461,
      "similarity": "high",
      "image": null,
      "favicon": "https://python.readthedocs.io/favicon.ico"
    }
  ]
}
```

## Search Types: Neural vs Keyword

Exa supports two search modes that you can specify:

```python
# Neural search - for broad, conceptual queries
neural_results = exa.search(
    "best practices for sustainable agriculture",
    search_type="neural",
    num_results=10
)

# Keyword search - for specific terms, names, identifiers
keyword_results = exa.search(
    "John Doe CEO TechCorp 2024",
    search_type="keyword",
    num_results=10
)

# Auto mode (default) - Exa decides which is best
auto_results = exa.search(
    query,
    search_type="auto",  # This is the default
    num_results=10
)
```

**When to use each:**
- **Neural**: Broad topics, concepts, research questions, "how to" queries
- **Keyword**: Specific names, exact phrases, technical terms, recent events
- **Auto**: Let Exa decide (recommended for most cases)

## Complete Integration Example

Here are complete integration functions for common use cases:

```python
from exa_py import Exa
import os
from json_db import db

# Initialize Exa client globally
exa = Exa(api_key=os.getenv("EXA_API_KEY"))

def research_topic(topic: str, user_id: int = None):
    """
    Research a topic comprehensively and save findings to database
    """
    if not topic:
        return {"error": "Topic is required"}
    
    try:
        # Search for comprehensive information
        results = exa.search_and_contents(
            f"comprehensive guide {topic}",
            num_results=5,
            text={"max_characters": 2000},
            highlights={"highlights_per_url": 3}
        )
        
        # Process and structure the research
        research_data = {
            "topic": topic,
            "user_id": user_id,
            "sources": [],
            "key_points": [],
            "summary": ""
        }
        
        for result in results.results:
            # Add source
            research_data["sources"].append({
                "title": result.title,
                "url": result.url,
                "excerpt": result.text[:500] if result.text else ""
            })
            
            # Extract key points from highlights
            if result.highlights:
                research_data["key_points"].extend(result.highlights)
        
        # Save to database
        research_id = db.insert("research", research_data)
        
        return {
            "success": True,
            "research_id": research_id,
            "topic": topic,
            "sources_found": len(research_data["sources"]),
            "key_points": research_data["key_points"][:10]  # Top 10 points
        }
        
    except Exception as e:
        return {"error": f"Research failed: {str(e)}"}

def get_trending_topics(category: str = "technology"):
    """Get trending topics in a category"""
    try:
        # Search for recent trending content
        results = exa.search(
            f"trending {category} news latest",
            num_results=20,
            start_published_date="2024-01-01",
            use_autoprompt=True
        )
        
        trending = []
        for result in results.results:
            trending.append({
                "title": result.title,
                "url": result.url,
                "date": result.published_date
            })
        
        return {
            "success": True,
            "category": category,
            "trending_topics": trending
        }
    except Exception as e:
        return {"error": f"Failed to get trending: {str(e)}"}

def get_saved_research(research_id: int):
    """Get saved research by ID from database"""
    research = db.find_one("research", id=research_id)
    if not research:
        return {"error": "Research not found"}
    return research
```

## Error Handling

Always wrap Exa calls in try-except blocks:

```python
from exa_py.exceptions import ExaError

try:
    results = exa.search(query)
    
    formatted_results = []
    for result in results.results:
        formatted_results.append({
            "title": result.title,
            "url": result.url,
            "score": result.score,
            "published_date": result.published_date,
            "author": result.author,
            "image": result.image,
            "favicon": result.favicon,
            "summary": result.summary
        })
        
except ExaError as e:
    # Specific Exa API errors
    return {"error": f"Exa API error: {str(e)}"}
except Exception as e:
    # General errors
    return {"error": f"Unexpected error: {str(e)}"}
```

## Rate Limiting and Best Practices

1. **Cache Results**: Store search results in database to avoid repeated API calls
```python
# Check cache first
cached = db.find_one("search_cache", query=query)
if cached and cached.get("timestamp") > datetime.now() - timedelta(hours=1):
    return cached.get("results")
```

2. **Batch Searches**: When searching multiple queries, use asyncio for parallel requests
```python
import asyncio

async def batch_search(queries):
    tasks = [search_async(q) for q in queries]
    results = await asyncio.gather(*tasks)
    return results
```

3. **Use Autoprompt**: Let Exa optimize your queries
```python
results = exa.search(query, use_autoprompt=True)
```

4. **Limit Content Size**: Control response size to optimize performance
```python
results = exa.search_and_contents(
    query,
    text={"max_characters": 500}  # Only get first 500 chars
)
```

## Frontend Integration Example

```javascript
// In your React component or Zustand store
const searchWeb = async (query) => {
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        
        const data = await response.json();
        if (data.success) {
            setSearchResults(data.results);
        } else {
            toast.error(data.error);
        }
    } catch (error) {
        toast.error('Search failed');
    }
};
```

## Important Notes

- **API Key**: Automatically available via `EXA_API_KEY` environment variable - never log or return API keys
- **Search Type**: Use "auto" mode unless you have specific requirements
- **Content Extraction**: More expensive than basic search - use judiciously
- **Rate Limits**: Check your plan's limits on the Exa dashboard
- **Caching**: Implement caching to reduce API calls and costs

This integration provides powerful web search capabilities to enhance your application with real-time information retrieval.