import requests

API_URL = "https://api.exa.ai/search"
API_KEY = "16fe8779-7264-44c1-a911-e8187cb629c6"

def search_exa(query, num_results=5):
    headers = {
        "accept": "application/json",
        "content-type": "application/json", 
        "x-api-key": API_KEY
    }
    
    payload = {
        "query": query,
        "numResults": num_results,
        "type": "neural"
    }
    
    response = requests.post(API_URL, headers=headers, json=payload)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

def get_content(ids):
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": API_KEY
    }
    
    payload = {
        "ids": ids,
        "text": True
    }
    
    response = requests.post("https://api.exa.ai/contents", headers=headers, json=payload)
    
    if response.status_code == 200:
        return response.json()
    return None

if __name__ == "__main__":
    results = search_exa("how to implement openai api with sending images")
    if results:
        for result in results["results"]:
            print(f"Title: {result['title']}")
            print(f"URL: {result['url']}")
            print("---")