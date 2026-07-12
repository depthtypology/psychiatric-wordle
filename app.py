from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os


app = Flask(__name__)

CORS(app)


client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)


SYSTEM_PROMPT = """
You are Psychiatric Doctordle AI.

You operate only using ICD-11 psychiatric classifications.

Rules:
- Only use ICD-11 diagnoses.
- Include ICD-11 codes.
- Do not invent disorders.
- Do not diagnose real users.
- This is an educational simulation.
"""


@app.route("/")
def home():
    return "Psychiatric Doctordle API online"


@app.route("/ask", methods=["POST"])
def ask():

    data = request.json

    question = data["question"]


    result = client.chat.completions.create(

        model="gpt-5-mini",

        messages=[
            {
                "role":"system",
                "content":SYSTEM_PROMPT
            },
            {
                "role":"user",
                "content":question
            }
        ]
    )


    return jsonify({

        "answer":
        result.choices[0].message.content

    })



if __name__ == "__main__":
    app.run()