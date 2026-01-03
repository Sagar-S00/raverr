"""
Test script to check the invite API response and status code
This will help debug why the API call fails on Linux server
"""

import json
import sys
from rave_api import RaveAPIClient
from rave_api.utils.helpers import get_invited_meshes

# Use the same credentials from bot_multi_example.py
device_id = "3e8e7a1a3514465ea7d5933cf855d22a"
auth_token = "318992d9edb53e2ae370c0777e0789be"

print("=" * 80)
print("Testing Invite API (/meshes/self)")
print("=" * 80)
print()

# Initialize API client
api_client = RaveAPIClient(auth_token=auth_token)

# Build the same request that get_invited_meshes makes
params = {
    "deviceId": device_id,
    "public": "true",
    "friends": "false",
    "local": "false",
    "invited": "true",
    "limit": 20,
    "lang": "en"
}

endpoint = "/meshes/self"
url = f"{api_client.base_url}{endpoint}"



try:
    # Make the request
    response = api_client.get(endpoint, params=params, timeout=15)
    
    # Print status code
    print(f"Status Code: {response.status_code}")
    print(response.json())
except Exception as e:
    print(f"Error: {e}")