import random
import os

TRIGGER_WORDS = {
    "soft": ["please", "baby", "mmm"],
    "medium": ["harder", "yes", "fuck"],
    "intense": ["daddy", "deeper", "cum"]
}

MOAN_AUDIO_PATHS = {
    "soft": ["moans/soft1.mp3", "moans/soft2.mp3"],
    "medium": ["moans/med1.mp3", "moans/med2.mp3"],
    "intense": ["moans/intense1.mp3", "moans/intense2.mp3"]
}

def get_moan_audio(text):
    text = text.lower()
    for level, keywords in TRIGGER_WORDS.items():
        if any(word in text for word in keywords):
            return random.choice(MOAN_AUDIO_PATHS[level])
    return None
