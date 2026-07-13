import os
import json
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route("/")
def home():
    return jsonify({"message": "API is working"})


@app.route("/api/generate-case", methods=["POST"])
def generate_case():
    api_key = os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        return jsonify({"error": "No API key"}), 500
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "Return only JSON: {\"presentation\": \"A patient case\", \"diagnosis\": \"schizophrenia\", \"hints\": [\"hallucinations\", \"delusions\", \"disorganized thinking\"]}"
                    },
                    {
                        "role": "user",
                        "content": "Generate a case"
                    }
                ],
                "max_tokens": 200
            }
        )
        
        if response.status_code != 200:
            return jsonify({"error": response.text}), 500
        
        content = response.json()["choices"][0]["message"]["content"]
        case = json.loads(content)
        return jsonify(case)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)