"""Ensemble batch card analysis script (majority-vote pipeline experiment).

Runs the same prompt/model combination N times per batch and majority-votes
the mechanic tags: a tag is kept only if it appears in at least --min-votes
runs (default: a strict majority). The tier for a kept tag is the most common
tier among the runs that tagged it (ties go to the stronger tier). This
directly attacks false positives, which are mostly stochastic.

Results are saved to public.labeled exactly like analyze_batch.py, but with
the model name suffixed (e.g. 'claude-fable-5+ens3'), so each ensemble
configuration shows up as its own prompt/model combo in the existing
accuracy report tooling:

    Rscript analysis/render_accuracy_report.R prompts/prompt13.md claude-fable-5+ens3

Usage:
    # 3-run majority vote (tag kept if present in >= 2 runs)
    uv run python analysis/analyze_batch_ensemble.py --prompt prompts/prompt13.md --model claude-fable-5

    # 5 runs, tag kept if present in >= 3
    uv run python analysis/analyze_batch_ensemble.py --prompt prompts/prompt13.md --model claude-opus-4-8 --runs 5

Note: for single-run temperature / batch-size experiments, use
analyze_batch.py, which already supports --temperature, --batch-size and
--save-model. Ensembling needs temperature > 0 so the runs actually differ
(default here is 1.0).
"""

import argparse
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Allow importing from the project root and the analysis dir
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

import claude_utils
from app import DEFAULT_MECHANICS
from analyze_batch import (
    CREATE_LABELED_TABLE,
    VALID_TABLES,
    fetch_cards,
    format_card_data,
    load_text_file,
    save_results,
)

TIER_ORDER = ["S+ Tier", "S-Tier", "A-Tier", "B-Tier", "C-Tier", "D-Tier"]


def parse_args():
    parser = argparse.ArgumentParser(description="Ensemble (majority-vote) MTG card analyzer")
    parser.add_argument("--prompt", required=True, help="Path to prompt template .md file")
    parser.add_argument("--mechanics", help="Path to mechanics .md file (default: app DEFAULT_MECHANICS)")
    parser.add_argument("--batch-size", type=int, default=10, help="Cards per API call (default: 10)")
    parser.add_argument("--model", default=claude_utils.DEFAULT_MODEL, help="Claude model to use")
    parser.add_argument("--runs", type=int, default=3, help="Independent runs per batch (default: 3)")
    parser.add_argument(
        "--min-votes",
        type=int,
        default=None,
        help="Runs a tag must appear in to be kept (default: strict majority of successful runs)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=1.0,
        help="Sampling temperature; must be > 0 for runs to differ (default: 1.0)",
    )
    parser.add_argument(
        "--save-model",
        default=None,
        help="Model name stored in public.labeled (default: <model>+ens<runs>)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip cards that already have a result in public.labeled for this prompt+save-model",
    )
    parser.add_argument(
        "--table",
        default="cards_to_analyze",
        choices=VALID_TABLES,
        help="Source table to read cards from (default: cards_to_analyze)",
    )
    return parser.parse_args()


def normalize_result(result):
    """Coerce a parsed API result into a list of {card_name, mech: tier} dicts."""
    if isinstance(result, dict):
        return [{"card_name": k, **v} for k, v in result.items() if isinstance(v, dict)]
    if isinstance(result, list):
        return [r for r in result if isinstance(r, dict)]
    return None


def tier_rank(tier: str) -> int:
    return TIER_ORDER.index(tier) if tier in TIER_ORDER else len(TIER_ORDER)


def vote_results(run_results: list[list[dict]], min_votes: int) -> list[dict]:
    """Merge per-run card results, keeping tags that appear in >= min_votes runs."""
    by_card = defaultdict(list)
    display_names = {}
    for run in run_results:
        for card in run:
            name = card.get("card_name") or card.get("name")
            if not name:
                continue
            key = name.lower()
            display_names.setdefault(key, name)
            by_card[key].append({k: v for k, v in card.items() if k not in ("card_name", "name")})

    merged = []
    for key, tag_dicts in sorted(by_card.items()):
        votes = Counter()
        tiers = defaultdict(list)
        for tags in tag_dicts:
            for mech, tier in tags.items():
                votes[mech] += 1
                tiers[mech].append(tier)

        result = {"card_name": display_names[key]}
        for mech, n in votes.items():
            if n >= min_votes:
                # most common tier among runs that tagged it; ties -> stronger tier
                tier_counts = Counter(tiers[mech])
                best = sorted(tier_counts.items(), key=lambda kv: (-kv[1], tier_rank(kv[0])))[0][0]
                result[mech] = best
        merged.append(result)
    return merged


def main():
    args = parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    if args.runs > 1 and args.temperature == 0:
        print("Warning: temperature 0 makes runs nearly identical; voting will not filter anything.", file=sys.stderr)

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

    save_model = args.save_model if args.save_model else f"{args.model}+ens{args.runs}"
    cards = fetch_cards(conn, args.prompt, save_model, args.skip_existing, args.table)
    total = len(cards)

    if total == 0:
        print("No cards to analyze.")
        conn.close()
        return

    batches = [cards[i : i + args.batch_size] for i in range(0, total, args.batch_size)]
    print(f"Model: {args.model}, runs={args.runs}, temperature={args.temperature} -> saving as '{save_model}'")
    print(f"Analyzing {total} cards in {len(batches)} batches of up to {args.batch_size}.")

    processed = 0
    for batch_num, batch in enumerate(batches, start=1):
        print(f"Batch {batch_num}/{len(batches)} ({len(batch)} cards)...", end=" ", flush=True)

        card_data = format_card_data(batch)
        prompt = claude_utils.build_prompt(prompt_template, card_data, mechanics)

        run_results = []
        for run_num in range(1, args.runs + 1):
            result, error = claude_utils.call_claude(api_key, prompt, args.model, args.temperature)
            if error is not None:
                err_dict, status = error
                print(f"[run {run_num} ERROR HTTP {status}: {err_dict.get('error')}]", end=" ", flush=True)
                continue
            normalized = normalize_result(result)
            if normalized is None:
                print(f"[run {run_num} ERROR: non-JSON response]", end=" ", flush=True)
                continue
            run_results.append(normalized)

        if not run_results:
            print("all runs failed — skipping batch.")
            continue

        min_votes = args.min_votes if args.min_votes is not None else len(run_results) // 2 + 1
        merged = vote_results(run_results, min_votes)

        n_raw = sum(len(card) - 1 for run in run_results for card in run)
        n_kept = sum(len(card) - 1 for card in merged)
        save_results(conn, merged, batch, args.prompt, save_model, args.table)
        processed += len(merged)
        print(
            f"done. {len(run_results)}/{args.runs} runs ok, min_votes={min_votes}, "
            f"tags {n_raw}->{n_kept} after vote. ({processed}/{total} total saved)"
        )

    conn.close()
    print(f"\nFinished. {processed}/{total} cards written to public.labeled as '{save_model}'.")


if __name__ == "__main__":
    main()
