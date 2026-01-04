"""
AI Utilities for Rave Bot
Handles Cloudflare Workers AI integration with group chat support
"""

import os
import json
import logging
import requests
from pathlib import Path
from typing import List, Dict, Optional
from cachetools import TTLCache
from datetime import timedelta
from openai import OpenAI

logger = logging.getLogger(__name__)

# Load system prompt from luci.txt
# Try to find luci.txt in the workspace root or current directory
_prompt_paths = [
    Path(__file__).parent.parent.parent / "luci.txt",  # Workspace root
    Path("luci.txt"),  # Current directory
    Path(__file__).parent.parent / "luci.txt",  # Parent of rave_api
]

SYSTEM_PROMPT = ""
for path in _prompt_paths:
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as file:
                SYSTEM_PROMPT = file.read()
            logger.info(f"Loaded system prompt from {path}")
        except Exception as e:
            logger.warning(f"Failed to load prompt from {path}: {e}")
        break

if not SYSTEM_PROMPT:
    logger.warning("System prompt not loaded, using default")
    SYSTEM_PROMPT = "You are Akane, a goth character with a dry, disinterested personality."

# Thread cache: keyed by mesh_id (room_id), TTL 24 hours
thread_cache = TTLCache(maxsize=1000, ttl=timedelta(hours=24).total_seconds())

# Perplexity API configuration (kept for backup)
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
PERPLEXITY_MODEL = "sonar-pro"

# Cloudflare Workers AI configuration
CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY", "DFAAcdEVHAKaV0ZhTFPoZYc7BMcEGi6-S2WTusuV")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "3860b8a7aef7b8c166e09fe254939799")
CLOUDFLARE_MODEL = "@hf/nousresearch/hermes-2-pro-mistral-7b"

# Initialize Cloudflare Workers AI client
cloudflare_client = OpenAI(
    api_key=CLOUDFLARE_API_KEY,
    base_url=f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/v1",
)

# EdenAI API configuration
EDENAI_API_KEY = os.getenv("EDENAI_API_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiYjczNzMwZDEtMDQ1Ny00ZjJhLTljOGEtNzczMzIwZDZmMWNlIiwidHlwZSI6ImZyb250X2FwaV90b2tlbiJ9.Oqqk9Ihpee6iim5JuPVHr1vEaImqKYSfdiNo3jMoYVE")


def get_thread_messages(mesh_id: str) -> List[Dict[str, str]]:
    """
    Get messages for a mesh thread, initializing with system prompt if new.
    
    Args:
        mesh_id: The mesh/room ID to get messages for
        
    Returns:
        List of message dictionaries with 'role' and 'content' keys
    """
    if mesh_id not in thread_cache:
        thread_cache[mesh_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return thread_cache[mesh_id]


def add_message(mesh_id: str, role: str, content: str):
    """
    Add a message to thread history.
    
    Args:
        mesh_id: The mesh/room ID
        role: Message role ('user', 'assistant', or 'system')
        content: Message content
    """
    messages = get_thread_messages(mesh_id)
    messages.append({"role": role, "content": content})
    thread_cache[mesh_id] = messages


def add_user_message(mesh_id: str, user_name: str, content: str):
    """
    Add a user message to thread history with group chat formatting.
    Formats message as "User: {user_name}: {content}" for group chat context.
    
    Args:
        mesh_id: The mesh/room ID
        user_name: Display name of the user sending the message
        content: Message content
    """
    formatted_content = f"User: {user_name}: {content}"
    add_message(mesh_id, "user", formatted_content)


def get_response77(mesh_id: str) -> Optional[str]:
    """
    Get AI response using Perplexity API for a given mesh (backup method).
    
    Args:
        mesh_id: The mesh/room ID to get response for
        
    Returns:
        AI-generated response text, or None if error
    """
    try:
        messages = get_thread_messages(mesh_id)
        
        client = OpenAI(
            base_url="https://api.perplexity.ai",
            api_key=PERPLEXITY_API_KEY
        )
        
        response = client.chat.completions.create(
            model=PERPLEXITY_MODEL,
            messages=messages
        )
        
        ai_response = response.choices[0].message.content
        
        # Add AI response to thread history
        if ai_response:
            add_message(mesh_id, "assistant", ai_response)
        
        return ai_response
        
    except Exception as e:
        logger.error(f"Error getting AI response for mesh {mesh_id}: {e}", exc_info=True)
        return None


def get_responseccc(mesh_id: str) -> Optional[str]:
    """
    Get AI response using Cloudflare Workers AI for a given mesh.
    
    Args:
        mesh_id: The mesh/room ID to get response for
        
    Returns:
        AI-generated response text, or None if error
    """
    try:
        messages = get_thread_messages(mesh_id)
        
        # Use chat completions with Cloudflare Workers AI
        chat_completion = cloudflare_client.chat.completions.create(
            messages=messages,
            model=CLOUDFLARE_MODEL,
        )
        
        ai_response = chat_completion.choices[0].message.content
        
        # Add AI response to thread history
        if ai_response:
            add_message(mesh_id, "assistant", ai_response)
        
        return ai_response
        
    except Exception as e:
        logger.error(f"Error getting AI response for mesh {mesh_id}: {e}", exc_info=True)
        return None


def clear_thread(mesh_id: str):
    """
    Clear conversation thread for a mesh (reset to system prompt only).
    
    Args:
        mesh_id: The mesh/room ID to clear
    """
    if mesh_id in thread_cache:
        thread_cache[mesh_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    else:
        # Initialize with system prompt
        thread_cache[mesh_id] = [{"role": "system", "content": SYSTEM_PROMPT}]


def get_response(mesh_id: str) -> Optional[str]:
    """
    Get AI response using EdenAI streaming API for a given mesh.
    
    Args:
        mesh_id: The mesh/room ID to get response for
        
    Returns:
        AI-generated response text, or None if error
    """
    try:
        messages = get_thread_messages(mesh_id)
        
        # Find the last user message from thread
        current_user_input = None
        for msg in reversed(messages):
            if msg["role"] == "user":
                current_user_input = msg["content"]
                break
        
        # Convert messages to EdenAI format (exclude system message and current user message)
        previous_history = []
        for msg in messages:
            if msg["role"] == "system":
                continue
            if msg["role"] == "user" and msg["content"] == current_user_input:
                continue
            previous_history.append({
                "role": msg["role"],
                "message": msg["content"]
            })
        
        if not current_user_input:
            logger.warning(f"No user input found for mesh {mesh_id}")
            return None
        
        headers = {
            'authority': 'api.edenai.run',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
            'authorization': f'Bearer {EDENAI_API_KEY}',
            'content-type': 'application/json',
            'origin': 'https://app.edenai.run',
            'referer': 'https://app.edenai.run/',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        json_data = {
            "providers": "perplexityai",
            "text": current_user_input,
            "temperature": 0.1,
            "max_tokens": 1000,
            "settings": {
                "perplexityai": "sonar-pro"
            },
            "previous_history": previous_history,
            "chatbot_global_action": SYSTEM_PROMPT,
            "response_as_dict": False
        }
        
        response = requests.post(
            'https://api.edenai.run/v2/text/chat/stream',
            headers=headers,
            json=json_data,
            stream=True
        )
        
        if response.status_code == 200:
            sentence = ''
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        response_data = json.loads(line)
                        text = response_data.get('text', '')
                        sentence += text
                    except json.JSONDecodeError as e:
                        logger.warning(f"Error decoding JSON in stream: {e}")
            
            ai_response = sentence
            if ai_response:
                add_message(mesh_id, "assistant", ai_response)
            
            return ai_response
        else:
            logger.error(f"EdenAI API returned status code {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting streaming AI response for mesh {mesh_id}: {e}", exc_info=True)
        return None

