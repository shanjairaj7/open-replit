import requests
import json
import re
import os
from openai import AzureOpenAI

# --- Context7 MCP Configuration ---
API_URL = "https://mcp.context7.com/mcp"
API_KEY = "ctx7sk-d145de59-27b3-49ce-89f3-680a21d4d508"

# --- Azure OpenAI Configuration ---
endpoint = "https://rajsu-m9qoo96e-eastus2.services.ai.azure.com"
model_name = "gpt-5-mini"
deployment = "gpt-5-mini"
api_version = "2024-12-01-preview"
subscription_key = os.environ.get('AZURE_SUBSCRIPTION_KEY', 'FMj8fTNAOYsSv4jMIq7W0CbHATRiQAUa0MQIR6wuqlS8vvaT6ZoSJQQJ99BDACHYHv6XJ3w3AAAAACOGVJL1')

azure_client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key,
)

# --- Context7 Functionality ---
def call_context7_tool(method_name, tool_name, arguments, request_id):
    """
    Calls a Context7 MCP tool using the correct JSON-RPC 2.0 format.
    Handles the SSE stream response and returns the full data content.
    """
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "X-Context7-Api-Key": API_KEY
    }
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method_name,
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, stream=True)
        response.raise_for_status()

        full_content = ""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        if 'error' in data:
                            print(f"MCP error: {data['error']['message']}")
                            return None
                        if 'result' in data and 'content' in data['result']:
                            if isinstance(data['result']['content'], dict) and 'text' in data['result']['content']:
                                full_content += data['result']['content']['text']
                            elif isinstance(data['result']['content'], list):
                                for item in data['result']['content']:
                                    if 'text' in item:
                                        full_content += item['text']
                    except json.JSONDecodeError:
                        pass
            
        return {"result": {"content": [{"type": "text", "text": full_content}]}}

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

def resolve_library_id(library_name):
    arguments = {"libraryName": library_name}
    tool_response = call_context7_tool("tools/call", "resolve-library-id", arguments, 1)

    if tool_response:
        content_text = tool_response['result']['content'][0]['text']
        
        best_library_id = None
        highest_trust = -1
        
        libraries = re.findall(r'Context7-compatible library ID: (.+?)\n(?:.*Trust Score: (\d+\.?\d*))?', content_text, re.DOTALL)
        
        for lib_id, trust in libraries:
            try:
                trust_score = float(trust) if trust else 0
                if trust_score > highest_trust:
                    highest_trust = trust_score
                    best_library_id = lib_id.strip()
            except ValueError:
                continue
        
        if not best_library_id and libraries:
            best_library_id = libraries[0][0].strip()
        
        return best_library_id

    return None

def get_library_docs(library_id, topic, max_snippets=5):
    arguments = {
        "context7CompatibleLibraryID": library_id,
        "topic": topic,
        "tokens": 1000
    }
    tool_response = call_context7_tool("tools/call", "get-library-docs", arguments, 2)
    
    if tool_response:
        full_text = tool_response['result']['content'][0]['text']
        
        if max_snippets and 'TITLE:' in full_text:
            parts = full_text.split('TITLE:')
            if len(parts) > max_snippets + 1:
                header = parts[0]
                selected_snippets = parts[1:max_snippets + 1]
                truncated_text = header + 'TITLE:' + 'TITLE:'.join(selected_snippets)
                truncated_text += f"\n\n... (showing {max_snippets} of {len(parts)-1} available snippets)"
                return truncated_text
        
        return full_text
    return None

# --- Azure OpenAI Integration ---
def query_into_search(query):
    """
    Uses Azure OpenAI to extract the library and search term from a user query.
    """
    response = azure_client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": """
For a given query, output the name of the package/library/provider/company to search for AND the question to ask in that search.

Let's say the query is: 'How to save images in a supabase database'
Your output should be:
<output>
<library>supabase</library>
<search>how to save images in the database</search>
</output>
"""},
            {"role": "user", "content": f'QUERY: {query}'}
        ],
        max_completion_tokens=10000,
    )
    
    message = response.choices[0].message.content
    
    library_match = re.search(r'<library>(.*?)<\/library>', message)
    search_match = re.search(r'<search>(.*?)<\/search>', message)
    
    library = library_match.group(1).strip() if library_match else None
    search = search_match.group(1).strip() if search_match else None

    print(library)
    print(search)
    
    return library, search

def generate_full_response(user_query):
    """
    Orchestrates the entire process: extracting search terms, fetching docs,
    and querying the LLM with the injected context.
    """
    # 1. Parse user query to get library and search term
    library_name, search_term = query_into_search(user_query)

    if not library_name or not search_term:
        return "Could not parse the query to find a library and search term."

    # 2. Get the library ID from Context7
    library_id = resolve_library_id(library_name)

    if not library_id:
        return f"Could not find a valid library ID for '{library_name}'."

    # 3. Get the docs from Context7 using the library ID
    docs = get_library_docs(library_id, search_term)

    return docs

# --- Example Usage ---
if __name__ == "__main__":
    user_query = "how to call send images to openai api with python"
    response = generate_full_response(user_query)
    print("Final Response from Azure OpenAI:")
    print(response)
