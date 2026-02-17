import json
import os

import anthropic
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

prompt_path = os.path.join(os.path.dirname(__file__), "prompt.md")
with open(prompt_path) as f:
    PROMPT_TEMPLATE = f.read()

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    if not API_KEY:
        return jsonify({"error": "ANTHROPIC_API_KEY environment variable is not set"}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    card_data = data.get("card_data", "").strip()

    if not card_data:
        return jsonify({"error": "Card data is required"}), 400

    prompt = PROMPT_TEMPLATE.replace("CARD_LIST_PLACEHOLDER", card_data)

    try:
        client = anthropic.Anthropic(api_key=API_KEY)
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

    # Strip markdown code fences if present (e.g. ```json\n...\n```)
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]  # remove opening ```json line
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        result = raw_text

    return jsonify({"result": result})


if __name__ == "__main__":
    app.run(debug=True)
