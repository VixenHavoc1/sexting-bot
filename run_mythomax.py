import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    print("Error: OPENROUTER_API_KEY is not set!")
else:
    print("OpenRouter API key loaded.")

def run_mythomax(prompt, history=None, persona="You are a flirty, horny anime girl who replies in character."):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    if not history:
        history = []

    messages = [{"role": "system", "content": persona}]
    messages += history
    messages.append({"role": "user", "content": prompt})

    body = {
        "model": "gryphe/mythomax-l2-13b",
        "messages": messages,
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=20  # optional: faster timeouts
        )

        print("Status Code:", response.status_code)
        print("Response Text:", response.text)

        if response.status_code == 200:
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            return content
        else:
            return "I'm having a bit of trouble responding right now. Try again in a sec 😢"

    except Exception as e:
        print("Exception:", e)
        return "Oops... something exploded internally 💥"

