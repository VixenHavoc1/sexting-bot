import json
import os
from datetime import datetime

STRUCTURED_MEMORY_FILE = "user_memory.json"

def load_structured_memory():
    if not os.path.exists(STRUCTURED_MEMORY_FILE):
        return {}
    with open(STRUCTURED_MEMORY_FILE, "r") as f:
        return json.load(f)

def save_structured_memory(memory):
    with open(STRUCTURED_MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def get_user_profile(user_id):
    memory = load_structured_memory()
    return memory.get(user_id, {})

def update_user_profile(user_id, updates):
    memory = load_structured_memory()
    user_data = memory.get(user_id, {})
    user_data.update(updates)
    user_data["last_seen"] = datetime.now().isoformat()
    memory[user_id] = user_data
    save_structured_memory(memory)

