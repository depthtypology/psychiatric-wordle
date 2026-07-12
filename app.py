import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


@app.route("/")
def index():
    return "Psychiatric Doctordle Backend Online"


@app.route("/api/generate-case", methods=["POST"])
def generate_case():
    try:
        if not OPENAI_API_KEY:
            return jsonify({"error": "API key not configured"}), 500

        system_message = """You are a psychiatric case generator for an educational game.
Generate a brief psychiatric case. Return ONLY this JSON structure, no other text:
{
    "presentation": "Brief 2-3 sentence patient description with symptoms",
    "diagnosis": "single diagnosis name in lowercase",
    "hints": ["hint 1", "hint 2", "hint 3"]
}"""

        user_message = "Generate a new psychiatric case using ICD-11 diagnoses."

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "gpt-4-mini",
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }

        api_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )

        if api_response.status_code != 200:
            return jsonify({
                "error": "OpenAI API failed",
                "status": api_response.status_code
            }), 500

        api_data = api_response.json()
        content = api_data["choices"][0]["message"]["content"]
        case = json.loads(content)

        return jsonify(case), 200

    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON from API"}), 500
    except requests.exceptions.Timeout:
        return jsonify({"error": "API request timeout"}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Request failed: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
