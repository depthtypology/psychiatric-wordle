import os
import json
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
                        "content": "You are a psychiatric case generator. Return ONLY valid JSON (no markdown, no extra text). Format: {\"presentation\": \"2-3 sentence case\", \"diagnosis\": \"diagnosis name\", \"hints\": [\"hint1\", \"hint2\", \"hint3\"]}"
                    },
                    {
                        "role": "user",
                        "content": "Generate a new psychiatric case using ICD-11 diagnoses"
                    }
                ],
                "max_tokens": 500,
                "temperature": 0.7
            },
            timeout=30
        )
        
        if response.status_code != 200:
            return {"error": f"OpenAI API error: {response.status_code}"}
        
        # Get the text content from OpenAI
        api_data = response.json()
        content_text = api_data["choices"][0]["message"]["content"]
        
        # Parse the JSON string into an object
        case_data = json.loads(content_text)
        
        # Make sure diagnosis is lowercase
        if "diagnosis" in case_data:
            case_data["diagnosis"] = case_data["diagnosis"].lower()
        
        return case_data
    
    except json.JSONDecodeError as e:
        return {"error": f"JSON parse error: {str(e)}"}
    except requests.exceptions.Timeout:
        return {"error": "API request timeout"}
    except Exception as e:
        return {"error": str(e)}
