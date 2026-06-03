import os
import re
import secrets

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from claude_utils import DEFAULT_MODEL, build_prompt, call_claude
from oauth_routes import oauth_bp

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Session configuration
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# For production with HTTPS:
if os.environ.get('FLASK_ENV') == 'production':
    app.config['SESSION_COOKIE_SECURE'] = True

app.register_blueprint(oauth_bp)

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")

prompt_path = os.path.join(os.path.dirname(__file__), "prompt.md")
with open(prompt_path) as f:
    PROMPT_TEMPLATE = f.read()

# Default mechanics definitions (extracted from prompt.md)
DEFAULT_MECHANICS = """- ramp: Accelerates your mana production (Birds of Paradise, Cultivate, Sol Ring, Dockside Extortionist). Includes treasures, rituals, and other effects which increase the amount of mana you have available.  Does not include mana fixing or untapping effects.
- card_advantage: Net positive card advantage giving you access to more than one card (Harmonize, Rhystic Study, Mulldrifter).  Does not include cantrips, cycling, card selection, or tutors unless they provide net positive card advantage (i.e. they give you more than one card).
- targeted_disruption: A single card which removes or interacts with a single target opponent card (Path to Exile, Counterspell, Cyclonic Rift). Includes targeted removal, bounce spells, ability disruption, tap effects, and counterspells.
- mass_disruption: A single card which affects multiple opponent cards or multiple opponents directly (Wrath of God, Cyclonic Rift, Rest in Peace). Includes mass removal, mass bounce, graveyard hate, and tap effects.
- go_wide: Card supports a "go_wide" strategy by creating additional tokens or creates.
- anthem: increases toughness or power of all creatures in the commander deck.
- overrun: Provides buffs to (multiple) creatures strength, power, evasivenss or ability to get through, enabling a large number of creatures to do a high level of damage
- go_tall: Increase a single creature's power or toughness
- equipment_tutor: search for equipment cards, stronger if the cards go directly onto the battlefield
- cheat_equip_cost: allow equipment to be attached directly to a creature for free, reduced, or other bonus cost
- get_through: trample, evasion, or other effects which allow a creature to get through defenders or otherwise discourage blocking
- protection: indestructible, shroud, or other effects which protect a creature(s)
- etb_effects: effects which provide value when the card enters the battlefield
- blink_flicker: temporarily removes a creature and returns it to the battlefield
- mana_sink: abilities which convert extra mana into value
- goad: force opponent's creatures to attack, preferably someone other than you"""


# --- Routes ---

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/default-mechanics", methods=["GET"])
def get_default_mechanics():
    """Return default mechanics for UI initialization."""
    return jsonify({"mechanics": DEFAULT_MECHANICS})


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON."}), 400

    card_data = data.get("card_data", "").strip()
    if not card_data:
        return jsonify({"error": "Card data is required"}), 400
    if len(card_data) > 50_000:
        return jsonify({"error": "Card data too large (max 50,000 characters)."}), 400

    mechanics = data.get("mechanics", "").strip() or DEFAULT_MECHANICS

    access_password = os.environ.get("ACCESS_PASSWORD", "").strip()
    if access_password:
        access_code = data.get("access_code", "").strip()
        if not access_code:
            return jsonify({"error": "Access code required.", "error_type": "access_code_required"}), 403
        if not secrets.compare_digest(access_code, access_password):
            return jsonify({"error": "Access denied: incorrect access code.", "error_type": "access_code_invalid"}), 403

    # Optional overrides
    model = data.get("model", "").strip() or DEFAULT_MODEL
    prompt_template_override = data.get("prompt_template")
    prompt_file = data.get("prompt_file")

    if prompt_template_override is not None and prompt_file is not None:
        return jsonify({"error": "Specify prompt_template or prompt_file, not both."}), 400

    if prompt_file is not None:
        if not re.fullmatch(r"[\w\-]+", prompt_file):
            return jsonify({"error": "Invalid prompt_file name."}), 400
        file_path = os.path.join(PROMPTS_DIR, prompt_file + ".md")
        if not os.path.isfile(file_path):
            return jsonify({"error": f"Prompt file '{prompt_file}' not found."}), 404
        with open(file_path) as f:
            active_template = f.read()
    elif prompt_template_override is not None:
        active_template = prompt_template_override
    else:
        active_template = PROMPT_TEMPLATE

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "Server is not configured with an API key. Set ANTHROPIC_API_KEY environment variable."}), 500

    prompt = build_prompt(active_template, card_data, mechanics)
    result, error = call_claude(api_key, prompt, model=model)
    if error:
        return jsonify(error[0]), error[1]

    return jsonify({"result": result, "model_used": model})


if __name__ == "__main__":
    # Production: use gunicorn (see render.yaml)
    # Local dev: python app.py (enables debug mode)
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)
