import json
import os

import anthropic
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

prompt_path = os.path.join(os.path.dirname(__file__), "prompt.md")
with open(prompt_path) as f:
    PROMPT_TEMPLATE = f.read()

ENV_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/config")
def config():
    return jsonify({"has_env_key": bool(ENV_API_KEY)})


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    api_key = data.get("api_key", "").strip() or ENV_API_KEY
    card_data = data.get("card_data", "").strip()

    if not api_key:
        return jsonify({"error": "API key is required"}), 400
    if not card_data:
        return jsonify({"error": "Card data is required"}), 400

    prompt = PROMPT_TEMPLATE.replace("CARD_LIST_PLACEHOLDER", card_data)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.AuthenticationError:
        return jsonify({"error": "Invalid API key"}), 401
    except anthropic.APIError as e:
        return jsonify({"error": f"API error: {e.message}"}), 502

    raw_text = message.content[0].text

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        result = raw_text

    return jsonify({"result": result})


if __name__ == "__main__":
    app.run(debug=True)
