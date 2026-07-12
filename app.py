from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import requests


app = Flask(__name__)

# Allow CORS from your domain
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://depthtypology.site", "http://localhost:3000", "http://localhost:5000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


SYSTEM_PROMPT = """You are a psychiatric case generator for an educational Doctordle game. 
Generate a brief, anonymized psychiatric case for diagnosis guessing. Use ICD-11 classifications.

Return ONLY valid JSON with no additional text:
{
    "presentation": "Patient's presenting symptoms and history (2-3 sentences)",
    "diagnosis": "The ICD-11 diagnosis (single name, lowercase)",
    "hints": [
        "Clue 1 about the diagnosis",
        "Clue 2 about the diagnosis",
        "Clue 3 about the diagnosis"
    ]
}"""


@app.route("/")
def home():
    return "Psychiatric Doctordle API online"


@app.route("/api/generate-case", methods=["POST", "OPTIONS"])
def generate_case():
    # Handle CORS preflight
    if request.method == "OPTIONS":
        return "", 204
    
    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4-mini",
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": "Generate a new psychiatric case."
                }
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(OPENAI_API_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return jsonify({"error": f"OpenAI API error: {response.status_code}"}), 500
        
        data = response.json()
        response_text = data["choices"][0]["message"]["content"]
        case_data = json.loads(response_text)
        
        return jsonify(case_data), 200

    except json.JSONDecodeError as e:
        return jsonify({"error": f"Failed to parse AI response: {str(e)}"}), 500
    except requests.exceptions.Timeout:
        return jsonify({"error": "OpenAI API request timed out"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to generate case: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
