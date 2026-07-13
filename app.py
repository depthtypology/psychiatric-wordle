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
                        "content": "Generate only JSON response with no markdown or extra text. Return this format exactly: {\"presentation\": \"brief patient case\", \"diagnosis\": \"single diagnosis name\", \"hints\": [\"hint 1\", \"hint 2\", \"hint 3\"]}"
                    },
                    {
                        "role": "user",
                        "content": "Generate a psychiatric case"
                    }
                ],
                "max_tokens": 300,
                "temperature": 0.7
            },
            timeout=30
        )
        
        if response.status_code != 200:
            return {"error": f"OpenAI error: {response.status_code}"}
        
        # Extract message content
        try:
            api_response = response.json()
            content = api_response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if not content:
                return {"error": "Empty response from OpenAI"}
            
            # Clean up potential markdown
            content = content.strip()
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            # Parse JSON
            case_data = json.loads(content)
            
            # Ensure required fields exist and are correct type
            if "presentation" not in case_data or "diagnosis" not in case_data or "hints" not in case_data:
                return {"error": "Invalid case format from AI"}
            
            # Lowercase diagnosis
            case_data["diagnosis"] = str(case_data["diagnosis"]).lower().strip()
            
            # Ensure hints is a list
            if not isinstance(case_data["hints"], list):
                case_data["hints"] = [str(case_data["hints"])]
            
            return case_data
            
        except json.JSONDecodeError as je:
            return {"error": f"JSON decode failed: {str(je)}, got: {content[:100]}"}
        
    except requests.exceptions.Timeout:
        return {"error": "Request timeout"}
    except Exception as e:
        return {"error": f"Error: {str(e)}"}
