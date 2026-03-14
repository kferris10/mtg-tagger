"""OAuth routes (dormant — app currently uses server-side ANTHROPIC_API_KEY)."""

import requests
from flask import Blueprint, jsonify, redirect, request, session

from oauth_manager import AnthropicOAuthManager

oauth_bp = Blueprint("oauth", __name__)
oauth_manager = AnthropicOAuthManager()


@oauth_bp.route("/login")
def login():
    """Initiate OAuth flow by redirecting to Anthropic authorization."""
    if not oauth_manager.CLIENT_ID:
        return jsonify({"error": "OAuth not configured. Set ANTHROPIC_OAUTH_CLIENT_ID environment variable."}), 500

    code_verifier, code_challenge = oauth_manager.generate_pkce_params()
    state = oauth_manager.generate_state()

    session['oauth_state'] = state
    session['pkce_verifier'] = code_verifier

    auth_url = oauth_manager.get_authorization_url(state, code_challenge)
    return redirect(auth_url)


@oauth_bp.route("/oauth/callback")
def oauth_callback():
    """Handle OAuth callback from Anthropic."""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')

    if error:
        return f"<h1>Authorization failed</h1><p>Error: {error}</p><a href='/'>Go back</a>", 400

    if not state or state != session.get('oauth_state'):
        return "<h1>Invalid state parameter</h1><p>Possible CSRF attack.</p><a href='/'>Go back</a>", 400

    code_verifier = session.get('pkce_verifier')
    if not code_verifier:
        return "<h1>Missing PKCE verifier</h1><p>Session expired or invalid.</p><a href='/login'>Try again</a>", 400

    try:
        token_data = oauth_manager.exchange_code_for_token(code, code_verifier)
        access_token = token_data['access_token']

        api_key = oauth_manager.create_api_key(access_token)

        session['anthropic_api_key'] = api_key
        session['authenticated'] = True

        session.pop('oauth_state', None)
        session.pop('pkce_verifier', None)

        return redirect('/')

    except requests.HTTPError as e:
        error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
        return f"<h1>OAuth failed</h1><p>Error: {error_detail}</p><a href='/login'>Try again</a>", 500
    except Exception as e:
        return f"<h1>Unexpected error</h1><p>{str(e)}</p><a href='/login'>Try again</a>", 500


@oauth_bp.route("/logout")
def logout():
    """Clear session and log out user."""
    session.clear()
    return redirect('/')


@oauth_bp.route("/auth/status")
def auth_status():
    """Return current authentication status (for frontend polling)."""
    return jsonify({
        "authenticated": session.get('authenticated', False)
    })
