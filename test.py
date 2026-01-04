import os
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

# =========================
# Initial test input
# =========================

INITIAL_USER_INPUT = "hello bitch are you dead?"

# =========================
# Models + seeded replies
# =========================

SEED_DATA = {
    "@cf/meta/llama-3.2-3b-instruct":
        "I'm not dead, I'm just having a worse day than you.",

    "@cf/mistral/mistral-7b-instruct-v0.1":
        "Akane: (squinting) What's your problem, Ass-tart?",

    "@cf/mistral/mistral-7b-instruct-v0.2-lora":
        "Akane: (rolling her eyes) Typical. Can't even form a proper greeting.",

    "@hf/mistral/mistral-7b-instruct-v0.2":
        "Akane: I'm alive, but barely. How about you, ass?",

    "@cf/meta/llama-3.3-70b-instruct-fp8-fast":
        "I'm alive, unfortunately.",

    "@cf/google/gemma-3-12b-it":
        "Ugh. Not even close.",

    "@hf/nousresearch/hermes-2-pro-mistral-7b":
        "oh, i'm so sorry. i didn't realize being called a bitch could bring me back to life. how exciting.",

    "@cf/qwen/qwq-32b":
        "Wow. That’s your opening line? I’m alive — barely impressed.",

    "@cf/defog/sqlcoder-7b-2":
        "Akane: deadpan. holy cringe. Tsk."
}

# =========================
# Build per-model memory
# =========================

conversation_history = {}

for model, assistant_reply in SEED_DATA.items():
    conversation_history[model] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": INITIAL_USER_INPUT},
        {"role": "assistant", "content": assistant_reply},
    ]

# =========================
# Continue conversation
# =========================

def continue_conversation(user_input: str):
    for model in conversation_history:
        try:
            # add user message
            conversation_history[model].append(
                {"role": "user", "content": user_input}
            )

            res = client.chat.completions.create(
                model=model,
                messages=conversation_history[model],
                temperature=0.7,
                max_tokens=200,
            )

            reply = res.choices[0].message.content.strip()

            # save assistant reply
            conversation_history[model].append(
                {"role": "assistant", "content": reply}
            )

            print(f"{model} : {reply}")

        except Exception as e:
            print(f"{model} : ERROR -> {e}")

# =========================
# Example usage
# =========================

if __name__ == "__main__":
    continue_conversation("that is why your tits are so small")

