import os
import json
import requests
from openai import OpenAI

# =========================
# Cloudflare config
# =========================

CLOUDFLARE_API_KEY = os.getenv(
    "CLOUDFLARE_API_KEY",
    ""
)
CLOUDFLARE_ACCOUNT_ID = os.getenv(
    "CLOUDFLARE_ACCOUNT_ID",
    ""
)

client = OpenAI(
    api_key=CLOUDFLARE_API_KEY,
    base_url=f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/v1",
)

# =========================
# Load system prompt
# =========================

with open("luci.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

# Initialize chat history dictionary
chat_history = {}

def streamai(user_input, chatId):
    headers = {
        'authority': 'api.edenai.run',
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
        'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiYjczNzMwZDEtMDQ1Ny00ZjJhLTljOGEtNzczMzIwZDZmMWNlIiwidHlwZSI6ImZyb250X2FwaV90b2tlbiJ9.Oqqk9Ihpee6iim5JuPVHr1vEaImqKYSfdiNo3jMoYVE',
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
   "providers":"perplexityai",
   "text":user_input,
   "temperature":0.1,
   "max_tokens":1000,
   "settings":{
      "perplexityai":"sonar-pro"
   },
   "previous_history":[
      
   ],
   "chatbot_global_action":SYSTEM_PROMPT,
   "response_as_dict":False
}
    response = requests.post('https://api.edenai.run/v2/text/chat/stream', headers=headers, json=json_data, stream=True)
    
    if response.status_code == 200:
        sentence = ''
        for line in response.iter_lines(decode_unicode=True):
            if line:
                try:
                    response_data = json.loads(line)
                    text = response_data.get('text', '')
                    sentence += text
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON: {e}")
        
        chat_history[chatId]["messages"].append({"role": "assistant", "message": sentence})
        return sentence
    else:
        return False

    

print(streamai("hello bitch are you dead?", "123"))