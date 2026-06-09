"""Add cards from tags-labeled - KF.csv that are missing from public.cards_to_analyze.

Usage (from project root):
    uv run python analysis/add_missing_cards.py
    uv run python analysis/add_missing_cards.py --csv analysis/tags-labeled\ -\ KF.csv
    uv run python analysis/add_missing_cards.py --dry-run
"""

import argparse
import csv
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DEFAULT_CSV = Path(__file__).parent / "tags-labeled - KF.csv"

# Land cards to exclude from the analysis queue
KNOWN_LANDS = frozenset({
    # Basic lands
    "Forest", "Island", "Mountain", "Plains", "Swamp",
    # Non-basic lands
    "Azorius Chancery", "Blossoming Sands", "Bonders' Enclave", "Buried Ruin",
    "Canopy Vista", "Chamber of Manipulation", "Command Tower", "Cryptic Caves",
    "Emergence Zone", "Evolving Wilds", "Fire Nation Palace", "Forge of Heroes",
    "Gates of Istfell", "Glacial Floodplain", "Krosan Verge", "Minas Tirith",
    "Mines of Moria", "Moorland Haunt", "Mosswort Bridge", "Myriad Landscape",
    "Mystifying Maze", "Opal Palace", "Path of Ancestry", "Pit of Offerings",
    "Reliquary Tower", "Restless Anchorage", "Rogue's Passage", "Sea of Clouds",
    "Seaside Citadel", "Secret Tunnel", "Selesnya Sanctuary", "Simic Growth Chamber",
    "Stirring Wildwood", "Terramorphic Expanse", "Thornwood Falls",
    "Valakut, the Molten Pinnacle", "War Room", "Windbrisk Heights",
})


def parse_args():
    parser = argparse.ArgumentParser(description="Sync KF-labeled cards into cards_to_analyze queue")
    parser.add_argument("--csv", default=str(DEFAULT_CSV), help="Path to the KF labels CSV")
    parser.add_argument("--dry-run", action="store_true", help="Report missing cards without inserting")
    return parser.parse_args()


def main():
    args = parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"Error: CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        kf_names = [row["name"].strip() for row in reader if row.get("name", "").strip()]

    print(f"KF CSV: {len(kf_names)} cards")

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
        cur.execute("SELECT card_name FROM public.cards_to_analyze")
        existing = {row[0].strip() for row in cur.fetchall()}

    missing = [name for name in kf_names if name not in existing and name not in KNOWN_LANDS]

    print(f"Already in queue: {len(existing)}")
    print(f"Missing from queue: {len(missing)}")

    if not missing:
        print("Nothing to add.")
        conn.close()
        return

    for name in missing:
        print(f"  + {name}")

    if args.dry_run:
        print("\nDry run — no rows inserted.")
        conn.close()
        return

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO public.cards_to_analyze (card_name, status) VALUES %s",
            [(name, "NOT_STARTED") for name in missing],
        )
    conn.commit()
    conn.close()

    print(f"\nInserted {len(missing)} cards with status NOT_STARTED.")


if __name__ == "__main__":
    main()
