# MTG Tagger

A web app that uses Claude AI to analyze Magic: The Gathering cards for Commander format mechanics and assign tier ratings.  

Paste your card list, get back a sortable table showing which cards do ramp, card advantage, disruption, and more — each rated from S+ Tier down to D-Tier based on Commander meta relevance.

## What it does

You paste a list of cards (in Archidekt export format), and the app sends them to Claude with a detailed analysis prompt. Claude evaluates each card against a defined set of Commander mechanics and rates the strength of each effect independently:

| Mechanic | Examples |
|---|---|
| `ramp` | Sol Ring, Cultivate, Dockside Extortionist |
| `card_advantage` | Rhystic Study, Harmonize, Mulldrifter |
| `targeted_disruption` | Path to Exile, Counterspell, Swords to Plowshares |
| `mass_disruption` | Wrath of God, Cyclonic Rift, Rest in Peace |
| `go_wide` | Token generators |
| `anthem` | Cards that buff all your creatures |
| `overrun` | Cards that push damage through |

Cards with no relevant mechanics show up in the table too — so you can easily spot filler.

You can also customize the mechanics list entirely to fit your own tagging taxonomy.

## Running it yourself

**Requirements:** Python 3.9+, [uv](https://docs.astral.sh/uv/), an Anthropic API key

```bash
git clone https://github.com/your-username/mtg-tagger
cd mtg-tagger
uv sync
cp .env.example .env
# edit .env and add your ANTHROPIC_API_KEY
uv run python app.py
```

Then open `http://localhost:5000`.

## Deployment

The app is configured for one-click deploy to [Render](https://render.com) via `render.yaml`. Set `ANTHROPIC_API_KEY` in the Render dashboard after deploying. Optionally set `ACCESS_PASSWORD` to require a shared access code before anyone can run an analysis.

## Developer docs

See [CLAUDE.md](CLAUDE.md) for architecture details, environment variable reference, and development commands.

## Credits

- **Built with [Claude Code](https://claude.ai/code)** — AI-assisted development by Anthropic
- **Analysis powered by [Claude](https://anthropic.com)** (Anthropic) via the Claude API
- **Card art** courtesy of [Scryfall](https://scryfall.com) — tier list art crops are fetched from the [Scryfall API](https://scryfall.com/docs/api). Card art is © Wizards of the Coast.
- **Magic: The Gathering** is © Wizards of the Coast. This project is an unofficial fan tool and is not affiliated with or endorsed by Wizards of the Coast.
