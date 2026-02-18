import json
import os
import secrets

import anthropic
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, session

from oauth_manager import AnthropicOAuthManager

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

oauth_manager = AnthropicOAuthManager()

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
- overrun: Provides buffs to (multiple) creatures strength, power, evasivenss or ability to get through, enabling a large number of creatures to do a high level of damage"""


@app.route("/login")
def login():
    """Initiate OAuth flow by redirecting to Anthropic authorization."""
    if not oauth_manager.CLIENT_ID:
        return jsonify({"error": "OAuth not configured. Set ANTHROPIC_OAUTH_CLIENT_ID environment variable."}), 500

    # Generate PKCE parameters
    code_verifier, code_challenge = oauth_manager.generate_pkce_params()
    state = oauth_manager.generate_state()

    # Store in session for callback verification
    session['oauth_state'] = state
    session['pkce_verifier'] = code_verifier

    # Redirect to Anthropic authorization
    auth_url = oauth_manager.get_authorization_url(state, code_challenge)
    return redirect(auth_url)


@app.route("/oauth/callback")
def oauth_callback():
    """Handle OAuth callback from Anthropic."""
    # Extract parameters
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')

    # Check for authorization errors
    if error:
        return f"<h1>Authorization failed</h1><p>Error: {error}</p><a href='/'>Go back</a>", 400

    # Validate state (CSRF protection)
    if not state or state != session.get('oauth_state'):
        return "<h1>Invalid state parameter</h1><p>Possible CSRF attack.</p><a href='/'>Go back</a>", 400

    # Retrieve PKCE verifier
    code_verifier = session.get('pkce_verifier')
    if not code_verifier:
        return "<h1>Missing PKCE verifier</h1><p>Session expired or invalid.</p><a href='/login'>Try again</a>", 400

    try:
        # Exchange code for access token
        token_data = oauth_manager.exchange_code_for_token(code, code_verifier)
        access_token = token_data['access_token']

        # Create permanent API key (simpler than managing token refresh)
        api_key = oauth_manager.create_api_key(access_token)

        # Store API key in session
        session['anthropic_api_key'] = api_key
        session['authenticated'] = True

        # Clean up OAuth parameters
        session.pop('oauth_state', None)
        session.pop('pkce_verifier', None)

        # Redirect to home page
        return redirect('/')

    except requests.HTTPError as e:
        error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
        return f"<h1>OAuth failed</h1><p>Error: {error_detail}</p><a href='/login'>Try again</a>", 500
    except Exception as e:
        return f"<h1>Unexpected error</h1><p>{str(e)}</p><a href='/login'>Try again</a>", 500


@app.route("/logout")
def logout():
    """Clear session and log out user."""
    session.clear()
    return redirect('/')


@app.route("/auth/status")
def auth_status():
    """Return current authentication status (for frontend polling)."""
    return jsonify({
        "authenticated": session.get('authenticated', False)
    })


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/default-mechanics", methods=["GET"])
def get_default_mechanics():
    """Return default mechanics for UI initialization."""
    return jsonify({"mechanics": DEFAULT_MECHANICS})


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    card_data = data.get("card_data", "").strip()
    if not card_data:
        return jsonify({"error": "Card data is required"}), 400

    # Get custom mechanics or use defaults
    mechanics = data.get("mechanics", "").strip() or DEFAULT_MECHANICS

    # Validate access code if ACCESS_PASSWORD is configured
    access_password = os.environ.get("ACCESS_PASSWORD", "").strip()
    if access_password:
        access_code = data.get("access_code", "").strip()
        if not access_code:
            return jsonify({"error": "Access code required.", "error_type": "access_code_required"}), 403
        if not secrets.compare_digest(access_code, access_password):
            return jsonify({"error": "Access denied: incorrect access code.", "error_type": "access_code_invalid"}), 403

    # Always use server-side API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "Server is not configured with an API key. Set ANTHROPIC_API_KEY environment variable."}), 500

    # Substitute both placeholders
    prompt = PROMPT_TEMPLATE.replace("CARD_LIST_PLACEHOLDER", card_data)
    prompt = prompt.replace("MECHANICS_PLACEHOLDER", mechanics)

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
    # Production: use gunicorn (see render.yaml)
    # Local dev: python app.py (enables debug mode)
    import os
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)
