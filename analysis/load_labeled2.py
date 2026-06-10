"""Load analysis/labeled2.csv into public.labeled_kf_final (PostgreSQL).

Drops and recreates the table on each run so re-running after edits is safe.

One row per card; the kf column is a JSONB object of {category: tier_kf} pairs
(rows with an empty tier_kf are excluded from the JSON).

Usage (from project root):
    uv run python analysis/load_labeled2.py
"""

import csv
import json
import os
from collections import defaultdict
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

CSV_PATH = Path(__file__).parent / "labeled2.csv"

CREATE_TABLE = """
CREATE TABLE public.labeled_kf_final (
    card_name TEXT PRIMARY KEY,
    kf        JSONB NOT NULL DEFAULT '{}'
);
"""


def load_csv(path: Path) -> dict[str, dict]:
    tags: dict[str, dict] = defaultdict(dict)
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tier = row["tier_kf"].strip()
            if tier:
                tags[row["card_name"]][row["category"]] = tier
    return tags


def main():
    tags = load_csv(CSV_PATH)

    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", 5432),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        dbname="mtgcards",
    )
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS public.labeled_kf_final")
                cur.execute(CREATE_TABLE)
                psycopg2.extras.execute_values(
                    cur,
                    "INSERT INTO public.labeled_kf_final (card_name, kf) VALUES %s",
                    [(name, json.dumps(kf)) for name, kf in sorted(tags.items())],
                    template="(%s, %s::jsonb)",
                )
        print(f"Wrote {len(tags)} rows to public.labeled_kf_final")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
