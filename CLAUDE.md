# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MTG Tagger is a Flask web app that uses the Anthropic API to analyze Magic: The Gathering cards for Commander format mechanics and tier ratings. Users provide an Anthropic API key and card data through a web UI, and the app sends the cards to Claude with a detailed prompt template (`prompt.md`) that defines the mechanics taxonomy and tier system.

## Commands

- **Install dependencies:** `uv sync`
- **Run the dev server:** `uv run python app.py` (starts Flask on localhost:5000 with debug mode)

## Architecture

- **`app.py`** — Flask application with two routes: `GET /` serves the UI, `POST /analyze` accepts card data + API key, substitutes cards into the prompt template, calls the Anthropic API, and returns JSON results.
- **`prompt.md`** — Prompt template with `CARD_LIST_PLACEHOLDER` that gets replaced with user-provided card data. Defines the mechanics to tag (ramp, card_advantage, targeted_disruption, mass_disruption, go_wide, anthem, overrun) and the tier system (S+ through D-Tier).
- **`templates/index.html`** — Single-page UI with inline CSS/JS. Collects API key and card data, POSTs to `/analyze`, displays JSON results.
- **`main.py`** — Placeholder entry point (unused by the web app).

## Card Data Format

Cards are provided as: `Name: card_name. Text: card_text` (one per line).

## Key Details

- Python 3.9, managed with `uv`
- The Anthropic API key is provided per-request by the user (not stored server-side)
- The API call uses `claude-sonnet-4-20250514`
