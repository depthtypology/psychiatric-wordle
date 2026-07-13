import os
import json
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://depthtypology.site",
        "http://localhost:3000",
        "http://localhost:5000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


@app.get("/")
def home():
    return {"message": "Psychiatric Doctordle API Online"}


@app.post("/api/generate-case")
def generate_case():
    if not OPENAI_API_KEY:
        return {"error": "API key not configured"}
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "Generate a psychiatric case. Return ONLY JSON: {\"presentation\": \"case\", \"diagnosis\": \"name\", \"hints\": [\"h1\", \"h2\", \"h3\"]}"
                    },
                    {
                        "role": "user",
                        "content": "Generate a psychiatric case"
                    }
                ],
                "max_tokens": 500
            }
        )
        
        if response.status_code != 200:
            return {"error": response.text}
        
        content = response.json()["choices"][0]["message"]["content"]
        case = json.loads(content)
        return case
    
    except Exception as e:
        return {"error": str(e)}
