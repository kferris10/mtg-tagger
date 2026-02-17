# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MTG Tagger is a Flask web app that uses the Anthropic API to analyze Magic: The Gathering cards for Commander format mechanics and tier ratings. Users authenticate via Anthropic Console OAuth and provide card data through a web UI. The app sends the cards to Claude with a detailed prompt template (`prompt.md`) that defines the mechanics taxonomy and tier system.

## Commands

- **Install dependencies:** `uv sync`
- **Setup environment:** Copy `.env.example` to `.env` and configure OAuth credentials
- **Run the dev server:** `uv run python app.py` (starts Flask on localhost:5000 with debug mode)

## Architecture

- **`app.py`** — Flask application with analysis route. `GET /` serves the UI, `POST /analyze` accepts card data and optional API key, substitutes cards into the prompt template, calls the Anthropic API, and returns JSON results. API key priority: request body > environment variable.
- **`prompt.md`** — Prompt template with `CARD_LIST_PLACEHOLDER` that gets replaced with user-provided card data. Defines the mechanics to tag (ramp, card_advantage, targeted_disruption, mass_disruption, go_wide, anthem, overrun) and the tier system (S+ through D-Tier).
- **`templates/index.html`** — Single-page UI with inline CSS/JS. Collects optional API key and card data, POSTs to `/analyze`, displays sortable results table with tier-ranked mechanics and individual card detail panel.
- **`main.py`** — Placeholder entry point (unused by the web app).
- **`.env`** — Local environment configuration (not committed). Contains optional `ANTHROPIC_API_KEY` for fallback authentication.
- **`.env.example`** — Template for environment variables.
- **`oauth_manager.py`** — OAuth 2.0 manager (unused, kept for potential future use).

## Authentication

The app supports **two authentication methods** with the following priority:

1. **User-provided API key** (entered in the UI) - highest priority
2. **Environment variable** (`ANTHROPIC_API_KEY`) - fallback

### Method 1: Manual API Key Entry (Recommended)

Simply enter your Anthropic API key in the web UI. Get your key from [console.anthropic.com](https://console.anthropic.com/) → Settings → API Keys.

Leave the field blank to use the environment variable fallback.

### Method 2: Environment Variable

Set `ANTHROPIC_API_KEY` in `.env` or your environment. This will be used as a fallback if no API key is entered in the UI.

## Card Data Format

Cards are provided as: `Name: card_name. Text: card_text` (one per line).

## Key Details

- Python 3.9, managed with `uv`
- Authentication via API key (user-provided or environment variable)
- API keys can be entered in the UI or set via `ANTHROPIC_API_KEY` environment variable
- The API call uses `claude-sonnet-4-20250514`
- Dependencies: Flask, Anthropic SDK, python-dotenv, requests
