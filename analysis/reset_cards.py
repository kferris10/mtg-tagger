"""Reset cards to NOT_STARTED in public.cards_to_analyze.

Usage:
    # Reset a specific list of cards by name
    uv run python analysis/reset_cards.py "Sol Ring" "Cultivate"

    # Reset all non-land cards from the KF CSV (useful between multi-combo runs)
    uv run python analysis/reset_cards.py --from-csv analysis/tags-labeled\ -\ KF.csv

    # Reset ALL cards
    uv run python analysis/reset_cards.py --all
"""

import argparse
import csv
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))
from add_missing_cards import KNOWN_LANDS


VALID_TABLES = ("cards_to_analyze", "cards_to_analyze2")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("cards", nargs="*", help="Card names to reset")
    parser.add_argument("--all", action="store_true", help="Reset ALL cards")
    parser.add_argument("--from-csv", metavar="FILE", help="Reset non-land cards from CSV (name column)")
    parser.add_argument("--table", default="cards_to_analyze", choices=VALID_TABLES)
    return parser.parse_args()


def connect():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", 5432),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        dbname="mtgcards",
    )


def main():
    args = parse_args()

    if not args.all and not args.from_csv and not args.cards:
        print("Error: provide card names, --from-csv, or --all.", file=sys.stderr)
        sys.exit(1)

    table = args.table
    conn = connect()
    with conn.cursor() as cur:
        if args.all:
            cur.execute(f"UPDATE public.{table} SET status = 'NOT_STARTED'")
        elif args.from_csv:
            csv_path = Path(args.from_csv)
            with csv_path.open(newline="", encoding="utf-8") as f:
                names = [
                    row["name"].strip() for row in csv.DictReader(f)
                    if row.get("name", "").strip() and row["name"].strip() not in KNOWN_LANDS
                ]
            cur.execute(
                f"UPDATE public.{table} SET status = 'NOT_STARTED' WHERE card_name = ANY(%s)",
                (names,),
            )
        else:
            cur.execute(
                f"UPDATE public.{table} SET status = 'NOT_STARTED' WHERE card_name = ANY(%s)",
                (args.cards,),
            )
        print(f"Reset {cur.rowcount} cards to NOT_STARTED.")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
