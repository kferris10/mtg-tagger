"""Two-pass batch card analysis script.

Pass 1: standard analysis using the given prompt template.
Pass 2: sends Pass 1 results back to Claude with a feedback/review prompt to catch errors.

Both pass results are stored in public.labeled_two_pass for comparison against ground truth.

Oracle text is resolved automatically: local public.cards first, then Scryfall for any gaps.

Usage:
    uv run python analysis/analyze_batch_two_pass.py \\
        --prompt prompts/prompt11.md \\
        --feedback-prompt prompts/feedback_prompt.md \\
        --model claude-opus-4-8
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

import claude_utils
from app import DEFAULT_MECHANICS

CREATE_TWO_PASS_TABLE = """
CREATE TABLE IF NOT EXISTS public.labeled_two_pass (
    id                   SERIAL PRIMARY KEY,
    card_name            TEXT NOT NULL,
    prompt_file          TEXT NOT NULL,
    feedback_prompt_file TEXT NOT NULL,
    model                TEXT NOT NULL,
    analyzed_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_json_pass1       JSONB,
    raw_json_final       JSONB
);
"""

VALID_TABLES = ("cards_to_analyze", "cards_to_analyze2")
SCRYFALL_COLLECTION_URL = "https://api.scryfall.com/cards/collection"
SCRYFALL_HEADERS = {"User-Agent": "mtg-tagger/1.0 (kevin.ferris10@gmail.com)"}


def parse_args():
    parser = argparse.ArgumentParser(description="Two-pass MTG card analyzer")
    parser.add_argument("--prompt", required=True, help="Path to Pass 1 prompt template .md file")
    parser.add_argument("--feedback-prompt", required=True, help="Path to Pass 2 feedback prompt template .md file")
    parser.add_argument("--mechanics", help="Path to mechanics .md file (default: app DEFAULT_MECHANICS)")
    parser.add_argument("--batch-size", type=int, default=20, help="Cards per API call (default: 20)")
    parser.add_argument("--model", default=claude_utils.DEFAULT_MODEL, help="Claude model to use")
    parser.add_argument("--temperature", type=float, default=None, help="Sampling temperature (default: API default)")
    parser.add_argument("--save-model", default=None, help="Override the model name stored in the DB")
    parser.add_argument("--limit", type=int, default=None, help="Process at most N cards (useful for testing)")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip cards already in public.labeled_two_pass for this prompt+feedback+model combo",
    )
    parser.add_argument(
        "--table",
        default="cards_to_analyze",
        choices=VALID_TABLES,
        help="Source table to read cards from (default: cards_to_analyze)",
    )
    return parser.parse_args()


def load_text_file(path: str, label: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: {label} file not found: {path}", file=sys.stderr)
        sys.exit(1)


def fetch_cards(conn, prompt_file: str, feedback_file: str, model: str, skip_existing: bool,
                table: str = "cards_to_analyze") -> list[dict]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if skip_existing:
            cur.execute(
                f"""
                SELECT c.id, c.card_name
                FROM public.{table} c
                WHERE c.status = 'NOT_STARTED'
                  AND NOT EXISTS (
                    SELECT 1 FROM public.labeled_two_pass l
                    WHERE l.card_name = c.card_name
                      AND l.prompt_file = %s
                      AND l.feedback_prompt_file = %s
                      AND l.model = %s
                  )
                ORDER BY c.id
                """,
                (prompt_file, feedback_file, model),
            )
        else:
            cur.execute(
                f"SELECT id, card_name FROM public.{table} WHERE status = 'NOT_STARTED' ORDER BY id"
            )
        return cur.fetchall()


def lookup_oracle_text(conn, card_names: list[str]) -> dict[str, str]:
    """Return name → oracle_text for all given card names.

    Tries public.cards first; falls back to Scryfall for any not found locally.
    Double-faced cards: concatenates both face texts with ' // ' separator.
    """
    # Local DB lookup
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT name, oracle_text FROM public.cards WHERE name = ANY(%s)",
            (card_names,),
        )
        oracle_map = {r["name"]: r["oracle_text"] for r in cur.fetchall() if r["oracle_text"]}

    missing = [n for n in card_names if n not in oracle_map]
    if not missing:
        return oracle_map

    print(f"  Fetching {len(missing)} card(s) from Scryfall...", end=" ", flush=True)

    # Scryfall /cards/named — handles DFCs correctly; try full name then front-face fallback.
    # Normalize curly apostrophes (U+2019) → straight (U+0027) for Scryfall matching.
    fetched = {}
    named_url = "https://api.scryfall.com/cards/named"
    for i, name in enumerate(missing):
        normalized = name.replace("’", "'")
        candidates = [normalized]
        if " // " in normalized:
            candidates.append(normalized.split(" // ")[0])  # front face only
        for candidate in candidates:
            resp = requests.get(named_url, params={"exact": candidate}, headers=SCRYFALL_HEADERS, timeout=15)
            if resp.ok:
                card = resp.json()
                if "card_faces" in card:
                    text = " // ".join(
                        face.get("oracle_text", "") for face in card["card_faces"]
                        if face.get("oracle_text")
                    )
                else:
                    text = card.get("oracle_text", "")
                if text:
                    fetched[name] = text  # store under original name
                    break
            time.sleep(0.1)
        if name not in fetched:
            time.sleep(0.1)  # still respect rate limit on failed lookups

    still_missing = [n for n in missing if n not in fetched]
    if still_missing:
        print(f"WARNING: no oracle text found for: {still_missing}", file=sys.stderr)

    print("done.")
    oracle_map.update(fetched)
    return oracle_map


def format_card_data(batch: list[dict], oracle_map: dict[str, str]) -> str:
    lines = []
    for row in batch:
        name = row["card_name"]
        text = oracle_map.get(name)
        lines.append(f"{name} | {text}" if text else name)
    return "\n".join(lines)


def normalize_results(result) -> list[dict]:
    """Normalize API result to a list of card dicts."""
    if isinstance(result, dict):
        return [{"card_name": k, **v} for k, v in result.items()]
    if isinstance(result, list):
        return result
    return []


def save_two_pass_results(conn, batch: list[dict], pass1_results: list[dict], final_results: list[dict],
                          prompt_file: str, feedback_file: str, model: str, table: str = "cards_to_analyze"):
    p1_by_name = {r.get("card_name", r.get("name", "")).lower(): r for r in pass1_results}
    final_by_name = {r.get("card_name", r.get("name", "")).lower(): r for r in final_results}
    batch_by_name = {row["card_name"].lower(): row["id"] for row in batch}

    all_name_lowers = set(p1_by_name.keys()) | set(final_by_name.keys())

    with conn.cursor() as cur:
        for name_lower in all_name_lowers:
            p1 = p1_by_name.get(name_lower)
            final = final_by_name.get(name_lower)
            representative = p1 or final
            card_name = representative.get("card_name") or representative.get("name") or name_lower

            cur.execute(
                """
                INSERT INTO public.labeled_two_pass
                    (card_name, prompt_file, feedback_prompt_file, model, raw_json_pass1, raw_json_final)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    card_name,
                    prompt_file,
                    feedback_file,
                    model,
                    json.dumps(p1) if p1 is not None else None,
                    json.dumps(final) if final is not None else None,
                ),
            )

            card_id = batch_by_name.get(name_lower)
            if card_id is not None:
                cur.execute(
                    f"UPDATE public.{table} SET status = 'COMPLETED' WHERE id = %s",
                    (card_id,),
                )

    conn.commit()


def main():
    args = parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    pass1_template = load_text_file(args.prompt, "prompt")
    feedback_template = load_text_file(args.feedback_prompt, "feedback-prompt")
    mechanics = load_text_file(args.mechanics, "mechanics") if args.mechanics else DEFAULT_MECHANICS

    try:
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            port=os.environ.get("DB_PORT", 5432),
            user=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            dbname="mtgcards",
        )
    except psycopg2.OperationalError as e:
        print(f"Error connecting to database: {e}", file=sys.stderr)
        sys.exit(1)

    with conn.cursor() as cur:
        cur.execute(CREATE_TWO_PASS_TABLE)
    conn.commit()

    save_model = args.save_model if args.save_model else args.model
    cards = fetch_cards(conn, args.prompt, args.feedback_prompt, save_model, args.skip_existing, args.table)
    if args.limit is not None:
        cards = cards[: args.limit]
    total = len(cards)

    if total == 0:
        print("No cards to analyze.")
        conn.close()
        return

    # Resolve oracle text for all cards up front
    all_names = [row["card_name"] for row in cards]
    oracle_map = lookup_oracle_text(conn, all_names)

    batches = [cards[i : i + args.batch_size] for i in range(0, total, args.batch_size)]
    temp_str = f", temperature={args.temperature}" if args.temperature is not None else ""
    print(f"Model: {args.model}{temp_str} -> saving as '{save_model}'")
    print(f"Analyzing {total} cards in {len(batches)} batches of up to {args.batch_size} (2 passes each).")

    processed = 0
    for batch_num, batch in enumerate(batches, start=1):
        print(f"Batch {batch_num}/{len(batches)} ({len(batch)} cards)...", end=" ", flush=True)

        card_data = format_card_data(batch, oracle_map)

        # Pass 1
        prompt1 = claude_utils.build_prompt(pass1_template, card_data, mechanics)
        pass1_result, error = claude_utils.call_claude(api_key, prompt1, args.model, args.temperature)

        if error is not None:
            err_dict, status = error
            print(f"ERROR pass1 (HTTP {status}): {err_dict.get('error')} — skipping batch.")
            continue

        pass1_list = normalize_results(pass1_result)
        if not pass1_list:
            print(f"ERROR pass1: unexpected result type {type(pass1_result).__name__} — skipping batch.")
            continue

        # Pass 2 — send pass1 JSON back for review
        pass1_json_str = json.dumps(pass1_result, indent=2)
        prompt2 = claude_utils.build_feedback_prompt(feedback_template, card_data, mechanics, pass1_json_str)
        final_result, error = claude_utils.call_claude(
            api_key, prompt2, args.model, args.temperature,
            system="Output only valid JSON. No explanations, no reasoning, no markdown — just the JSON object.",
        )

        if error is not None:
            err_dict, status = error
            print(f"ERROR pass2 (HTTP {status}): {err_dict.get('error')} — saving pass1 only.")
            final_list = []
        else:
            final_list = normalize_results(final_result)
            if not final_list:
                print(f"WARNING pass2: unexpected result type {type(final_result).__name__} — saving pass1 only.")

        save_two_pass_results(conn, batch, pass1_list, final_list,
                              args.prompt, args.feedback_prompt, save_model, args.table)
        processed += len(pass1_list)
        print(f"done. ({processed}/{total} total saved)")

    conn.close()
    print(f"\nFinished. {processed}/{total} cards written to public.labeled_two_pass.")


if __name__ == "__main__":
    main()
