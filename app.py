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

prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "prompt12.md")
with open(prompt_path) as f:
    PROMPT_TEMPLATE = f.read()

# Default mechanics definitions (from analysis/mechanics.md)
DEFAULT_MECHANICS = """- ramp: Increases your mana production above the curve by adding new mana sources or mana itself (Birds of Paradise, Cultivate, Sol Ring, Dockside Extortionist). Includes treasures, rituals, and other effects which increase the amount of mana you have available.  Does not include mana fixing or untapping effects.
- card_advantage: Net positive card advantage giving you access to 1+ more cards than you spent to cast (Harmonize, Rhystic Study, Mulldrifter). Does not include cantrips, cycling, card selection, or tutors unless they provide net positive card advantage (i.e. they net you more cards than you spent)
- targeted_disruption: A single card which removes or interacts with a single target opponent card (Path to Exile, Counterspell, Cyclonic Rift). Includes targeted removal, bounce spells, ability disruption, tap effects, and counterspells.
- mass_disruption: A single card which affects multiple opponent cards or multiple opponents directly (Wrath of God, Cyclonic Rift, Rest in Peace). Includes mass removal, mass bounce, graveyard hate, and tap effects.
- go_wide: Creates multiple creature tokens or scales token production (Raise the Alarm, Avenger of Zendikar).
- anthem: PERSISTENT static or triggered buff to power/toughness of multiple creatures you control (Glorious Anthem, tribal lords). Does NOT include one-turn combat bursts (see overrun).
- overrun: ONE-SHOT combat burst granting power, toughness, or evasion to multiple creatures for one attack (Overrun, Craterhoof Behemoth). Distinguished from anthem by being temporary.
- go_tall: Permanently or persistently increases a SINGLE creature's power or toughness numbers (Blackblade Reforged, Bear Umbra, Tuvasa the Sunlit). Includes auras and equipment with a static +X/+X boost or scaling growth. Does NOT include type-wide buffs (see anthem). Does NOT include indestructible or hexproof — those are protection, not go_tall.
- equipment_tutor: Searches for equipment cards (Stoneforge Mystic). Higher tier if the equipment enters the battlefield directly.
- cheat_equip_cost: Attaches equipment for free or at reduced cost (Puresteel Paladin, Sigarda's Aid).
- get_through: A creature has, or a card grants, evasion that allows dealing combat damage despite blockers: flying, trample, shadow, menace, intimidate, unblockable (Whispersilk Cloak, Trailblazer's Boots). Tag a creature if it NATURALLY has evasion as a meaningful function. Tag equipment/auras that grant evasion. Does NOT include: (a) go_wide cards whose tokens happen to have evasion — tag go_wide; (b) double strike or first strike — combat damage bonuses, not evasion; (c) anthem effects that buff flying creatures.
- protection: means a permanent cannot be Damaged, Enchanted/equipped, Blocked, or Targeted by source(s) (Lightning Greaves, Darksteel Plate, Fleecemane Lion, Jareth Leonine Titan). This is about immunity from these effects. Does NOT include: (a) blink/flicker effects — Cloudshift, Ephemerate, Momentary Blink, and Whitemane Lion are blink_flicker, NOT protection; (b) first strike, vigilance, or trample.
- etb_effects: An ETB (enters-the-battlefield) trigger that generates meaningful value (Mulldrifter draws cards, Acidic Slime destroys a permanent, Whitemane Lion returns a creature). Tag whenever the ETB provides meaningful value, even if that value is also captured by another mechanic — a creature that draws a card on ETB gets both etb_effects and card_advantage.
- untap_effects: Untaps permanents to generate extra mana or enable repeated abilities (Seedborn Muse, Wilderness Reclamation). Higher tier for untapping multiple permanents or untapping on each opponent's turn.
- blink_flicker: Temporarily exiles and returns a permanent to trigger ETB abilities (Conjurer's Closet, Ephemerate, Teleportation Circle).
- mana_sink: a card or ability that allows you to repeatedly pour large amounts of unspent mana into it for a proportional advantage (Jazal Goldmane, Kemba Kha Enduring, Leafdrake Roost, Temur Sabertooth). The defining trait: extra mana always has a productive outlet.
- goad: Forces opponent creatures to attack each combat, and goaded creatures cannot attack the goading player (Marisi Breaker of the Coil, Disrupt Decorum). Higher tier for multiple or repeatable goad."""


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
