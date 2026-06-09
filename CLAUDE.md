# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MTG Tagger is a Flask web app that uses the Anthropic API to analyze Magic: The Gathering cards for Commander format mechanics and tier ratings. Users submit card data through a web UI; the server calls Claude with a prompt template (`prompt.md`) that defines the mechanics taxonomy and tier system, then returns a JSON result rendered as a sortable table.

## Commands

- **Install dependencies:** `uv sync`
- **Run the dev server:** `uv run python app.py` (Flask on localhost:5000, debug mode)
- **Run tests:** `uv run pytest`
- **Run a single test:** `uv run pytest test_app.py::ClassName::test_name`
- **Setup environment:** Copy `.env.example` to `.env` and fill in values

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Server-side Anthropic key; never exposed to users |
| `FLASK_SECRET_KEY` | Yes (production) | Flask session signing key |
| `ACCESS_PASSWORD` | No | Shared access code for the UI; if unset, no code is required |
| `FLASK_ENV` | No | Set to `production` to enable secure cookies |

## Architecture

**Request flow:** Browser → `POST /analyze` → substitute card data + mechanics into `prompt.md` → Anthropic API → parse JSON response → return to UI → render sortable table.

- **`app.py`** — Flask app. `GET /` serves the UI. `POST /analyze` validates the access code (if `ACCESS_PASSWORD` is set), reads the server-side `ANTHROPIC_API_KEY`, substitutes `CARD_LIST_PLACEHOLDER` and `MECHANICS_PLACEHOLDER` in `prompt.md`, calls the Anthropic API (`claude-sonnet-4-20250514`, max 4096 tokens), strips any markdown code fences from the response, parses JSON, and returns `{"result": ...}`. Input is capped at 50,000 characters. `GET /api/default-mechanics` returns the built-in mechanics definitions for UI initialization.
- **`prompt.md`** — Prompt template with two placeholders: `CARD_LIST_PLACEHOLDER` (card list) and `MECHANICS_PLACEHOLDER` (mechanic definitions). Defines the tier system (S+ through D-Tier) and analysis instructions.
- **`templates/index.html`** — Single-page UI with inline CSS/JS. Fetches `/api/default-mechanics` on load, submits card data + optional access code + optional custom mechanics to `/analyze`, and renders a sortable results table with a card detail panel.
- **`oauth_manager.py`** — OAuth 2.0 manager. Routes `/login`, `/oauth/callback`, `/logout`, `/auth/status` exist in `app.py` but the OAuth flow is dormant; the app currently uses only the server-side `ANTHROPIC_API_KEY`.
- **`test_app.py`** — pytest test suite. Note: some tests reflect an older design where users could provide their own API key; those tests may not match current behavior.

## Batch Analysis Pipeline

Scripts in `analysis/` test prompt/model combinations against a PostgreSQL database (`mtgcards`, `public` schema). Ground-truth labels live in `analysis/tags-labeled - KF.csv`.

### Database tables
- **`public.cards_to_analyze`** — card queue (`id`, `card_name`, `status`: `NOT_STARTED` / `COMPLETED`)
- **`public.labeled`** — per-card results (`card_name`, `prompt_file`, `model`, `analyzed_at`, `raw_json` JSONB)

DB credentials (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`) are loaded from `.env` via `python-dotenv`.

### Key scripts

| Script | Purpose |
|---|---|
| `analysis/analyze_batch.py` | Run a prompt/model combo against all `NOT_STARTED` cards; saves results to `public.labeled` and marks cards `COMPLETED` |
| `analysis/add_missing_cards.py` | Add cards from KF CSV that are missing from the queue (excludes lands via `KNOWN_LANDS`) |
| `analysis/reset_cards.py` | Reset card status to `NOT_STARTED` (by name, `--from-csv`, or `--all`) |
| `analysis/render_accuracy_report.R` | Render a parameterized Quarto accuracy report for a given prompt + model |

### Analyze cards for a new prompt/model combo

```bash
# Analyze all NOT_STARTED cards
uv run python analysis/analyze_batch.py --prompt prompts/prompt2.md --model claude-opus-4-8

# Skip cards already labeled for this exact prompt+model (useful after partial runs)
uv run python analysis/analyze_batch.py --prompt prompts/prompt2.md --model claude-opus-4-8 --skip-existing

# If Claude returns non-JSON for a batch, retry with batch-size 1
uv run python analysis/analyze_batch.py --prompt prompts/prompt2.md --model claude-opus-4-8 --skip-existing --batch-size 1
```

### Re-analyze all cards with a new prompt/model (reset → run)

```bash
# Reset all cards to NOT_STARTED
uv run python analysis/reset_cards.py --all

# Then run the new combo
uv run python analysis/analyze_batch.py --prompt prompts/prompt2.md --model claude-sonnet-4-6
```

### Run the same cards through multiple combos

Reset cards by name between each run so only those cards are re-queued:

```bash
uv run python analysis/reset_cards.py "Card Name 1" "Card Name 2" ...
uv run python analysis/analyze_batch.py --prompt prompts/prompt.md --model claude-opus-4-8 --skip-existing
# repeat reset + run for each combo
```

### Restore COMPLETED status after an accidental reset

```sql
-- Mark any card COMPLETED if it has at least one labeled result
UPDATE public.cards_to_analyze c
SET status = 'COMPLETED'
WHERE EXISTS (SELECT 1 FROM public.labeled l WHERE l.card_name = c.card_name);
```

### Generate / regenerate accuracy reports

```bash
# Single report — output goes to analysis/accuracy-report-<prompt>-<model>.html
Rscript analysis/render_accuracy_report.R prompts/prompt2.md claude-opus-4-8

# All current combos
Rscript analysis/render_accuracy_report.R prompts/prompt.md  claude-sonnet-4-20250514
Rscript analysis/render_accuracy_report.R prompts/prompt.md  claude-sonnet-4-6
Rscript analysis/render_accuracy_report.R prompts/prompt.md  claude-opus-4-8
Rscript analysis/render_accuracy_report.R prompts/prompt2.md claude-sonnet-4-6
Rscript analysis/render_accuracy_report.R prompts/prompt2.md claude-opus-4-8
```

Reports are self-contained HTML files saved to `analysis/`.

## Card Data Format

Archidekt export format: `Name: card_name. Text: card_text` (one per line).

## Deployment

Deployed to Render via `render.yaml`. Build: `pip install .`. Start: `gunicorn app:app`. `FLASK_SECRET_KEY` is auto-generated by Render; `ANTHROPIC_API_KEY` and `ACCESS_PASSWORD` must be set manually in the Render dashboard.
