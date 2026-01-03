import os
from openai import OpenAI
from typing import List, Dict
import requests


# Initialize Cloudflare Workers AI client
CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY", "4c_KdIglpx-8qjF_qwnasZYSlMsjFwKCOfSaBZjc")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "3860b8a7aef7b8c166e09fe254939799")

openai = OpenAI(
    api_key=CLOUDFLARE_API_KEY,
    base_url=f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/v1",
)


# Example 1: Use chat completions
def chat_completion_example():
    """Use chat completions"""
    chat_completion = openai.chat.completions.create(
        messages=[{"role": "user", "content": "Make some robot noises"}],
        model="@cf/meta/llama-3.1-8b-instruct",
    )
    return chat_completion


# Example 2: Use responses (Cloudflare-specific endpoint)
# Note: The responses endpoint is Cloudflare-specific and may not be available
# through the standard OpenAI SDK. Using direct HTTP request as fallback.
def responses_example():
    """Use responses (Cloudflare-specific endpoint)"""
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/v1/responses"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "@cf/openai/gpt-oss-120b",
        "input": "Talk to me about open source",
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()


# Example 3: Use embeddings
def embeddings_example():
    """Use embeddings"""
    embeddings = openai.embeddings.create(
        model="@cf/baai/bge-large-en-v1.5",
        input="I love matcha",
    )
    return embeddings


# Example usage
if __name__ == "__main__":
    # Test chat completions
    print("Testing chat completions...")
    try:
        result = chat_completion_example()
        print(f"Response: {result.choices[0].message.content}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test responses
    print("\nTesting responses...")
    try:
        result = responses_example()
        print(f"Response: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test embeddings
    print("\nTesting embeddings...")
    try:
        result = embeddings_example()
        print(f"Embedding dimensions: {len(result.data[0].embedding)}")
        print(f"First 5 values: {result.data[0].embedding[:5]}")
    except Exception as e:
        print(f"Error: {e}")
