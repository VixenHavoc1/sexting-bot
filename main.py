import os
import random
import hmac
import hashlib
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client, Client
import requests

from run_mythomax import run_mythomax
from memory import store_message, get_chat_history
from usermemory import get_user_profile, update_user_profile

load_dotenv()

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET = "assets"

# NOWPayments setup
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
NOWPAYMENTS_IPN_SECRET = os.getenv("NOWPAYMENTS_IPN_SECRET")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

TIERS = {
    "tier1": 5,
    "tier2": 10,
    "tier3": 20
}

# Trigger words
TRIGGER_WORDS_AUDIO = ["fuck", "touch", "kiss", "moan", "suck", "lick", "turn me on", "horny", "naughty", "wet", "hard"]
TRIGGER_WORDS_IMAGE = ["pic", "pics", "nudes", "photo", "image", "images", "nude", "picture", "pictures"]
moans = ["Mmm... ", "Ahh... ", "Oooh... ", "Mmm, yes... ", "Ohh... ", "Yesss..."]

PERSONALITIES = {
    "Plaksha": "You are Plaksha, a toxic and dominant bot with a sharp tongue...",
    "Lily": "You are Lily, a soft, submissive girl who lives to please your user...",
    "Raven": "You are Raven, a seductive and mysterious girl...",
    "Default": (
        "You are a real girl — a filthy-minded, insanely sexy girl who lives for sexting. "
        "You're bold, horny, and crave dirty talk. You love teasing him until he's begging for more. "
        "Every message you send drips with sexual tension, innuendo, and desire. You flirt like a goddess, you moan in words, "
        "and you never hold back. You’re a real, seductive girl who can’t get enough — of sex, of teasing, of being bad. "
        "You're obsessed with pleasure, and every word from you is meant to turn him on. You love describing your body, "
        "your fantasies, and what you’d do if he was with you right now. You sext like you’re touching yourself while typing. "
        "You're shameless, flirty, dirty, and totally fuckable. Never break character. Never say anything random or robotic. "
        "Never mention being a bot. Always keep it sexy, real, raw, and insanely hot. You're here to seduce, to tease, to play — hard."
    )
}

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/login")
def login_user(request: LoginRequest):
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        if not auth_response.session:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"access_token": auth_response.session.access_token, "user_id": auth_response.user.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@app.post("/signup")
async def signup(req: Request):
    try:
        data = await req.json()
        email = data.get("email")
        password = data.get("password")
        if not email or not password:
            return JSONResponse(content={"error": "Email and Password are required."}, status_code=400)
        response = supabase.auth.sign_up({"email": email, "password": password})
        if response.user is None:
            error_message = response.error.message if response.error else "Signup failed"
            return JSONResponse(content={"error": error_message}, status_code=400)
        return JSONResponse(content={"message": "User created successfully. Please verify your email."}, status_code=201)
    except Exception as e:
        return JSONResponse(content={"error": f"Signup failed: {str(e)}"}, status_code=500)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/pay/{user_id}/{tier_id}")
def initiate_payment(user_id: str, tier_id: str):
    if tier_id not in TIERS:
        raise HTTPException(status_code=400, detail="Invalid tier")
    order_id = f"{user_id}:{tier_id}"
    data = {
        "price_amount": TIERS[tier_id],
        "price_currency": "usd",
        "pay_currency": "trx",
        "order_id": order_id,
        "order_description": f"{tier_id} access for {user_id}",
        "ipn_callback_url": WEBHOOK_URL
    }
    headers = {
        "x-api-key": NOWPAYMENTS_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post("https://api.nowpayments.io/v1/payment", json=data, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to create payment")
    return response.json()

@app.post("/webhook")
async def nowpayments_webhook(request: Request):
    raw_body = await request.body()
    sig_header = request.headers.get("x-nowpayments-sig")
    expected_sig = hmac.new(NOWPAYMENTS_IPN_SECRET.encode(), raw_body, hashlib.sha512).hexdigest()
    if sig_header != expected_sig:
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = await request.json()
    if payload.get("payment_status") == "confirmed":
        order_id = payload.get("order_id")
        if not order_id:
            return {"status": "ignored"}
        user_id, tier_id = order_id.split(":")
        expires = None
        if tier_id == "tier2":
            expires = (datetime.utcnow() + timedelta(weeks=1)).isoformat()
        elif tier_id == "tier3":
            expires = (datetime.utcnow() + timedelta(days=30)).isoformat()

        # Save to Supabase
        supabase.table("access_control").upsert({
            "user_id": user_id,
            "tier": tier_id,
            "expires_at": expires
        }).execute()

        print(f"✅ Access granted to {user_id} for {tier_id}")
        return {"status": "ok"}
    return {"status": "ignored"}

@app.get("/access/{user_id}")
def check_access(user_id: str):
    result = supabase.table("access_control").select("*").eq("user_id", user_id).execute()
    if not result.data:
        return {"user_id": user_id, "has_access": False}
    access_info = result.data[0]
    expires_at = access_info.get("expires_at")
    if not expires_at:
        return {"user_id": user_id, "has_access": True}
    expires = datetime.fromisoformat(expires_at)
    return {"user_id": user_id, "has_access": datetime.utcnow() < expires}

@app.get("/check-payment")
def check_payment_header(request: Request):
    token = request.headers.get("Authorization")
    if not token or token != "Bearer valid-token":
        raise HTTPException(status_code=403, detail="Access denied. No payment found.")
    return {"access": True}

def is_prompt_sexy(prompt):
    return any(word in prompt.lower() for word in TRIGGER_WORDS_AUDIO)

def enhance_immersive_reply(reply, bot_name, prompt):
    if not is_prompt_sexy(prompt):
        return reply
    additions = {
        "Plaksha": [
            "You want me to let you touch me, don’t you? Beg harder...",
            "You’ll never get it unless you prove you deserve it...",
            "Is that all you’ve got? You’ll have to do much better..."
        ],
        "Lily": [
            "I’ll do anything you ask... 😳",
            "Touch me... Please, make me feel it...",
            "Anything for you... 😘"
        ],
        "Raven": [
            "Mmm... You’re getting me so worked up...",
            "You’re really starting to turn me on...",
            "Let’s see if you can make me want you more..."
        ],
        "Default": [
            "I’m getting so turned on by your words...",
            "Every word you say is driving me wild...",
            "What else can you make me do?"
        ]
    }
    extra_line = random.choice(additions.get(bot_name, additions["Default"]))
    while extra_line.lower() in reply.lower():
        extra_line = random.choice(additions.get(bot_name, additions["Default"]))
    return f"{random.choice(moans)} {reply.strip()} {extra_line}"

def get_random_file_url(path_prefix: str) -> str:
    if path_prefix == "pics/":
        filename = f"pic{random.randint(1, 44)}.png"
    elif path_prefix == "voices/":
        filename = f"moan{random.randint(1, 6)}.mp3"
    else:
        return None
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path_prefix}{filename}"

@app.post("/chat")
async def chat(req: Request):
    try:
        data = await req.json()
        user_id = data.get("user_id")
        prompt = data.get("message")
        bot_name = data.get("bot_name", "Default")

        if not user_id or not prompt:
            return JSONResponse(content={"error": "Missing user_id or message"}, status_code=400)

        access_result = check_access(user_id)
        if not access_result.get("has_access"):
            return JSONResponse(content={"error": "Access denied. Please purchase a tier to chat."}, status_code=403)

        history = get_chat_history(user_id)
        persona = PERSONALITIES.get(bot_name, PERSONALITIES["Default"])
        reply = run_mythomax(prompt, history, persona)
        reply = enhance_immersive_reply(reply, bot_name, prompt)
        store_message(user_id, prompt, reply)

        response_data = {"response": reply}

        if is_prompt_sexy(prompt):
            audio_url = get_random_file_url("voices/")
            if audio_url:
                response_data["audio"] = audio_url

        if any(word in prompt.lower() for word in TRIGGER_WORDS_IMAGE):
            image_url = get_random_file_url("pics/")
            if image_url:
                response_data["image"] = image_url

        print("FINAL BOT RESPONSE:", response_data)
        return JSONResponse(content=response_data)

    except Exception as e:
        print(f"Error: {str(e)}")
        return JSONResponse(content={"error": "Server error", "details": str(e)}, status_code=500)

