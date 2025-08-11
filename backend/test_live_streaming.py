import os
from openai import AzureOpenAI

endpoint = "https://rajsu-m9qoo96e-eastus2.openai.azure.com/"
model_name = "gpt-5-mini"
deployment = "gpt-5-mini"

subscription_key = "FMj8fTNAOYsSv4jMIq7W0CbHATRiQAUa0MQIR6wuqlS8vvaT6ZoSJQQJ99BDACHYHv6XJ3w3AAAAACOGVJL1"
api_version = "2024-12-01-preview"

client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key,
)

response = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant.",
        },
        {
            "role": "user",
            "content": "I am going to Paris, what should I see?",
        }
    ],
    max_completion_tokens=16384,
    model=deployment,
    stream=True,
    stream_options={"include_usage": True}  # Request usage information in streaming
)

print("Streaming response:")
print("=" * 80)
full_response = ""
usage_info = None
chunk_count = 0

chunks_list = []

for chunk in response:
    chunk_count += 1
    chunks_list.append(chunk)
    
    # Log first 3 chunks in detail
    if chunk_count <= 3:
        print(f"\n[CHUNK {chunk_count}] Raw chunk: {chunk}")
        print(f"[CHUNK {chunk_count}] Type: {type(chunk)}")
        if hasattr(chunk, 'model_dump'):
            print(f"[CHUNK {chunk_count}] Model dump: {chunk.model_dump()}")
    
    # Process content
    if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
        delta = chunk.choices[0].delta
        if hasattr(delta, 'content') and delta.content:
            content = delta.content
            full_response += content
    
    # Check for usage information
    if hasattr(chunk, 'usage') and chunk.usage:
        usage_info = chunk.usage
        print(f"\n[CHUNK {chunk_count}] *** USAGE FOUND: {chunk.usage} ***")

# Log last 3 chunks
print(f"\n\nTotal chunks: {chunk_count}")
print("\nLast 3 chunks:")
for i, chunk in enumerate(chunks_list[-3:], start=len(chunks_list)-2):
    print(f"\n[CHUNK {i}] Raw chunk: {chunk}")
    if hasattr(chunk, 'model_dump'):
        print(f"[CHUNK {i}] Model dump: {chunk.model_dump()}")

print("\n\nFull response collected:")
print(full_response)

# Display usage information
if usage_info:
    print(f"\nUsage: {usage_info}")
else:
    print("\nNo usage information available in streaming response")