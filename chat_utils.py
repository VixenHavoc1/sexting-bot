import requests

# 🌶️ This function handles sending text to Eleven Labs and getting back audio
def generate_dynamic_audio(text, tone="default", pitch="default"):
    voice_id = "XB0fDUnXU5powFXDhCwa"  # Replace this with Charlotte’s actual voice ID
    api_key = "sk_2027679046c8111219cd03f7fb7d143754352f1a215e0f92"  # Put your ElevenLabs API key here

    # Clean text and add emotional style if needed (optional for later)
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,  # Lower = more expressive
            "similarity_boost": 0.8,  # Higher = closer to voice
            "style": 0.7,  # Intensity of emotion/style
            "use_speaker_boost": True
        }
    }

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        audio_data = response.content
        # You'll later send this to frontend or save it to a file
        return audio_data
    else:
        print("Audio generation failed:", response.text)
        return None

