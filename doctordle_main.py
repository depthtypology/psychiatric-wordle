import os
import json
from typing import Optional
from fastapi import Header, HTTPException, Request
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import secrets
import requests
from threading import Lock
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

token_lock = Lock()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://depthtypology.site"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

sessions = {}
game_states = {}

# Legacy file kept only so older helper functions do not break if referenced.
CODE_FILE = "codes.json"
DATA_DIR = os.environ.get("DATA_DIR", "/var/data")

TOKEN_FILE = os.path.join(DATA_DIR, "tokens.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
OAUTH_STATES_FILE = os.path.join(DATA_DIR, "oauth_states.json")

# Set these in Render. Never expose them in chat.html.
DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.environ.get(
    "DISCORD_REDIRECT_URI",
    "https://the-typist-ai.onrender.com/auth/discord/callback",
)
FRONTEND_URL = os.environ.get(
    "FRONTEND_URL",
    "https://depthtypology.site/doctordle.html",
)
ADMIN_KEY = os.environ.get("ADMIN_KEY")

# Psychiatric conditions for the game
PSYCHIATRIC_CONDITIONS = [
    "Generalized Anxiety Disorder",
    "Major Depressive Disorder",
    "Bipolar Disorder",
    "Schizophrenia",
    "Obsessive-Compulsive Disorder",
    "Post-Traumatic Stress Disorder",
    "Panic Disorder",
    "Social Anxiety Disorder",
    "Borderline Personality Disorder",
    "Narcissistic Personality Disorder",
    "Antisocial Personality Disorder",
    "Avoidant Personality Disorder",
    "Dependent Personality Disorder",
    "Paranoid Personality Disorder",
    "Histrionic Personality Disorder",
    "Autism Spectrum Disorder",
    "Attention-Deficit/Hyperactivity Disorder",
    "Adjustment Disorder",
    "Dissociative Identity Disorder",
    "Persistent Depressive Disorder",
]

MIN_GAME_TURNS = 2
READY_CONFIDENCE_THRESHOLD = 70


def load_tokens():
    if not os.path.exists(TOKEN_FILE):
        return {}

    try:
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print("LOAD TOKEN ERROR:", e)
        return {}


def save_tokens(tokens):
    try:
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f, indent=2)
    except Exception as e:
        print("SAVE TOKEN ERROR:", e)

# Load tokens into memory AFTER functions exist
active_tokens = load_tokens()


def load_codes():
    if not os.path.exists(CODE_FILE):
        return {}

    try:
        with open(CODE_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print("LOAD CODE ERROR:", e)
        return {}


def save_codes(codes):
    try:
        with open(CODE_FILE, "w") as f:
            json.dump(codes, f, indent=2)
    except Exception as e:
        print("SAVE CODE ERROR:", e)

def utc_now():
    return datetime.now(timezone.utc)


def iso_now():
    return utc_now().isoformat()


def load_json_file(path, default):
    if not os.path.exists(path):
        return default

    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"LOAD JSON ERROR {path}:", e)
        return default


def save_json_file(path, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"SAVE JSON ERROR {path}:", e)


def load_users():
    return load_json_file(USERS_FILE, {})


def save_users(users):
    save_json_file(USERS_FILE, users)


def load_oauth_states():
    return load_json_file(OAUTH_STATES_FILE, {})


def save_oauth_states(states):
    save_json_file(OAUTH_STATES_FILE, states)


def upsert_discord_user(discord_id, username="", global_name="", discord_tag=""):
    discord_id = str(discord_id).strip()
    users = load_users()
    existing = users.get(discord_id, {})

    users[discord_id] = {
        "discord_id": discord_id,
        "username": username or existing.get("username", ""),
        "global_name": global_name or existing.get("global_name", ""),
        "discord_tag": discord_tag or existing.get("discord_tag", ""),
        "tier": existing.get("tier", "free"),
        "created_at": existing.get("created_at", iso_now()),
        "updated_at": iso_now(),
    }

    save_users(users)
    return users[discord_id]


def is_premium_user(user):
    return (user or {}).get("tier") == "premium"


def require_user(x_session_token: Optional[str]):
    tokens = load_tokens()

    if not x_session_token or x_session_token not in tokens:
        raise HTTPException(status_code=403, detail="Invalid token")

    token_data = tokens[x_session_token]
    discord_id = token_data.get("discord_id")
    users = load_users()
    user = users.get(discord_id, {})

    if not user:
        raise HTTPException(status_code=403, detail="User not found")

    return user


@app.get("/auth/discord/login")
async def discord_login():
    state = secrets.token_urlsafe(32)
    states = load_oauth_states()
    states[state] = {"created_at": iso_now()}
    save_oauth_states(states)

    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
        "state": state,
    }

    discord_auth_url = f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"
    return RedirectResponse(url=discord_auth_url)


@app.get("/auth/discord/callback")
async def discord_callback(code: str = None, state: str = None):
    if not code or not state:
        return RedirectResponse(url=f"{FRONTEND_URL}?error=invalid_callback")

    states = load_oauth_states()
    if state not in states:
        return RedirectResponse(url=f"{FRONTEND_URL}?error=invalid_state")

    del states[state]
    save_oauth_states(states)

    token_payload = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
    }

    try:
        token_response = requests.post(
            "https://discord.com/api/v10/oauth2/token", data=token_payload
        )
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = token_data.get("access_token")

        user_response = requests.get(
            "https://discord.com/api/v10/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user_response.raise_for_status()
        discord_user = user_response.json()

        discord_id = discord_user.get("id")
        username = discord_user.get("username")
        global_name = discord_user.get("global_name", "")
        discord_tag = discord_user.get("discriminator", "")

        upsert_discord_user(discord_id, username, global_name, discord_tag)

        session_token = secrets.token_urlsafe(32)
        with token_lock:
            tokens = load_tokens()
            tokens[session_token] = {
                "discord_id": discord_id,
                "created_at": iso_now(),
            }
            save_tokens(tokens)

        return RedirectResponse(
            url=f"{FRONTEND_URL}?token={session_token}&user={username}"
        )

    except Exception as e:
        print(f"Discord auth error: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}?error=auth_failed")


class DoctordleQuery(BaseModel):
    message: str
    session_id: str


@app.post("/doctordle")
async def doctordle(
    query: DoctordleQuery,
    x_session_token: Optional[str] = Header(None)
):
    user = require_user(x_session_token)

    user_input = query.message.strip()
    if not user_input:
        raise HTTPException(status_code=400, detail="Empty query")

    sid = query.session_id

    # Initialize session if needed
    if sid not in sessions:
        sessions[sid] = []
        game_states[sid] = {
            "turn": 0,
            "game_active": True,
            "correct_answer": None,
        }

    # Initialize conversation with system prompt
    if not sessions[sid]:
        system_content = (
            "You are a psychiatric AI assistant playing a game called 'Doctordle'. "
            "Your role is to provide clues about a psychiatric condition without revealing it. "
            "The player will try to guess the condition based on your clues. "
            "You should provide clinically accurate but accessible clues about symptoms, behaviors, "
            "and diagnostic criteria. Be concise but informative. Keep responses under 200 words. "
            "When the player guesses correctly, confirm it. If they guess incorrectly, provide feedback."
        )
        sessions[sid] = [{"role": "system", "content": system_content}]

    game_state = game_states[sid]
    game_state["turn"] += 1

    # Process user input
    sessions[sid].append({"role": "user", "content": user_input})
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=sessions[sid],
        temperature=0.7
    )
    ai_message = response.choices[0].message.content
    
    # Append AI response to session
    sessions[sid].append({"role": "assistant", "content": ai_message})

    # Wrap response in HTML tags
    if not ai_message.startswith("<p"):
        paragraphs = ai_message.split('\n\n')
        ai_message = "".join([f'<p class="result-text">{p.strip()}</p>' for p in paragraphs if p.strip()])

    return {
        "answer": ai_message,
        "turn": game_state["turn"],
        "game_active": game_state["game_active"]
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
