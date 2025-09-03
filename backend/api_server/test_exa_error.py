#!/usr/bin/env python3
"""
Test script to reproduce the Exa.ai Result.__init__() error
"""

import os
from exa_py import Exa

# Initialize Exa client (use the API key)
exa = Exa(api_key="16fe8779-7264-44c1-a911-e8187cb629c6")

def test_comprehensive_research(company_name="google"):
    """Test the same searches that are failing"""
    
    sources = {
        "wikipedia": f"{company_name} site:wikipedia.org company",
        "github": f"{company_name} site:github.com organization", 
        "linkedin": f"{company_name} site:linkedin.com company",
        "crunchbase": f"{company_name} site:crunchbase.com organization"
    }
    
    all_results = {}
    for source, query in sources.items():
        try:
            print(f"==> Testing {source} search with query: '{query}'")
            results = exa.search(
                query,
                num_results=2,  # Small number for testing
                use_autoprompt=True
            )
            
            print(f"   Raw result type: {type(results)}")
            print(f"   Number of results: {len(results.results)}")
            
            # Try to access result attributes to see what's available
            if results.results:
                first_result = results.results[0]
                print(f"   First result type: {type(first_result)}")
                print(f"   First result dir: {[attr for attr in dir(first_result) if not attr.startswith('_')]}")
                
                # Try accessing each attribute
                for attr in ['title', 'url', 'score', 'published_date', 'author', 'image', 'text']:
                    try:
                        value = getattr(first_result, attr, None)
                        print(f"   {attr}: {type(value)} = {value}")
                    except Exception as e:
                        print(f"   {attr}: ERROR = {e}")
            
            all_results[source] = "SUCCESS"
            
        except Exception as e:
            print(f"   ERROR: {str(e)}")
            all_results[source] = {"error": str(e)}
    
    return all_results

if __name__ == "__main__":
    print("🔍 Testing Exa.ai searches that are causing errors")
    print("=" * 60)
    
    results = test_comprehensive_research()
    
    print(f"\n📊 Summary:")
    for source, result in results.items():
        status = "✅" if result == "SUCCESS" else "❌"
        print(f"{status} {source}: {result}")