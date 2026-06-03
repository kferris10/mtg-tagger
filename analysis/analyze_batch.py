"""Batch card analysis script.

Reads card names from public.cards_to_analyze (status = 'NOT_STARTED'), calls the
Anthropic API in batches, writes per-card results to public.labeled, and marks each
analyzed card COMPLETED in the source table.

Usage:
    uv run python analysis/analyze_batch.py --prompt prompt.md
    uv run python analysis/analyze_batch.py --prompt prompts/v2.md --batch-size 10 --skip-existing
"""

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

# Allow importing from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import claude_utils
from app import DEFAULT_MECHANICS

CREATE_LABELED_TABLE = """
CREATE TABLE IF NOT EXISTS public.labeled (
    id          SERIAL PRIMARY KEY,
    card_name   TEXT NOT NULL,
    prompt_file TEXT NOT NULL,
    model       TEXT NOT NULL,
    analyzed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_json    JSONB
);
"""


def parse_args():
    parser = argparse.ArgumentParser(description="Batch MTG card analyzer")
    parser.add_argument("--prompt", required=True, help="Path to prompt template .md file")
    parser.add_argument("--mechanics", help="Path to mechanics .md file (default: app DEFAULT_MECHANICS)")
    parser.add_argument("--batch-size", type=int, default=20, help="Cards per API call (default: 20)")
    parser.add_argument("--model", default=claude_utils.DEFAULT_MODEL, help="Claude model to use")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip cards that already have a result in public.labeled for this prompt file",
    )
    return parser.parse_args()


def load_text_file(path: str, label: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: {label} file not found: {path}", file=sys.stderr)
        sys.exit(1)


def fetch_cards(conn, prompt_file: str, skip_existing: bool) -> list[dict]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if skip_existing:
            cur.execute(
                """
                SELECT c.id, c.card_name
                FROM public.cards_to_analyze c
                WHERE c.status = 'NOT_STARTED'
                  AND NOT EXISTS (
                    SELECT 1 FROM public.labeled l
                    WHERE l.card_name = c.card_name
                      AND l.prompt_file = %s
                  )
                ORDER BY c.id
                """,
                (prompt_file,),
            )
        else:
            cur.execute(
                "SELECT id, card_name FROM public.cards_to_analyze WHERE status = 'NOT_STARTED' ORDER BY id"
            )
        return cur.fetchall()


def format_card_data(batch: list[dict]) -> str:
    return "\n".join(row["card_name"] for row in batch)


def save_results(conn, results: list, batch: list[dict], prompt_file: str, model: str):
    batch_by_name = {row["card_name"].lower(): row["id"] for row in batch}

    with conn.cursor() as cur:
        for card_result in results:
            card_name = card_result.get("card_name") or card_result.get("name")
            if not card_name:
                print(f"  Warning: skipping result with no card_name: {card_result}", file=sys.stderr)
                continue

            cur.execute(
                """
                INSERT INTO public.labeled (card_name, prompt_file, model, raw_json)
                VALUES (%s, %s, %s, %s)
                """,
                (card_name, prompt_file, model, json.dumps(card_result)),
            )

            card_id = batch_by_name.get(card_name.lower())
            if card_id is not None:
                cur.execute(
                    "UPDATE public.cards_to_analyze SET status = 'COMPLETED' WHERE id = %s",
                    (card_id,),
                )

    conn.commit()


def main():
    args = parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    prompt_template = load_text_file(args.prompt, "prompt")
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
        cur.execute(CREATE_LABELED_TABLE)
    conn.commit()

    cards = fetch_cards(conn, args.prompt, args.skip_existing)
    total = len(cards)

    if total == 0:
        print("No cards to analyze.")
        conn.close()
        return

    batches = [cards[i : i + args.batch_size] for i in range(0, total, args.batch_size)]
    print(f"Analyzing {total} cards in {len(batches)} batches of up to {args.batch_size}.")

    processed = 0
    for batch_num, batch in enumerate(batches, start=1):
        print(f"Batch {batch_num}/{len(batches)} ({len(batch)} cards)...", end=" ", flush=True)

        card_data = format_card_data(batch)
        prompt = claude_utils.build_prompt(prompt_template, card_data, mechanics)

        result, error = claude_utils.call_claude(api_key, prompt, args.model)

        if error is not None:
            err_dict, status = error
            print(f"ERROR (HTTP {status}): {err_dict.get('error')} — skipping batch.")
            continue

        if isinstance(result, dict):
            result = [{"card_name": k, **v} for k, v in result.items()]
        elif not isinstance(result, list):
            print(f"ERROR: expected JSON object or list, got {type(result).__name__} — skipping batch.")
            continue

        save_results(conn, result, batch, args.prompt, args.model)
        processed += len(result)
        print(f"done. ({processed}/{total} total saved)")

    conn.close()
    print(f"\nFinished. {processed}/{total} cards written to public.labeled.")


if __name__ == "__main__":
    main()
