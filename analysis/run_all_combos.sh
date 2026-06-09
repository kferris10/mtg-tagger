#!/usr/bin/env bash
# Runs all prompt/model combos sequentially.
# Each combo: reset all cards to NOT_STARTED, then analyze with --skip-existing.
# Run from project root: bash analysis/run_all_combos.sh

set -e
cd "$(dirname "$0")/.."

COMBOS=(
  "prompts/prompt.md claude-sonnet-4-20250514"
  "prompts/prompt.md claude-sonnet-4-6"
  "prompts/prompt.md claude-opus-4-8"
  "prompts/prompt2.md claude-sonnet-4-6"
  "prompts/prompt2.md claude-opus-4-8"
  "prompts/prompt3.md claude-opus-4-8"
  "prompts/prompt4.md claude-sonnet-4-6"
  "prompts/prompt4.md claude-opus-4-8"
  "prompts/prompt5.md claude-opus-4-8"
  "prompts/prompt6.md claude-opus-4-8"
  "prompts/prompt7.md claude-opus-4-8"
  "prompts/prompt8.md claude-opus-4-8"
  "prompts/prompt9.md claude-opus-4-8"
  "prompts/prompt10.md claude-opus-4-8"
  "prompts/prompt10.md claude-sonnet-4-6"
)

TOTAL=${#COMBOS[@]}
IDX=1

for COMBO in "${COMBOS[@]}"; do
  PROMPT=$(echo "$COMBO" | awk '{print $1}')
  MODEL=$(echo "$COMBO"  | awk '{print $2}')
  echo ""
  echo "=== Combo $IDX/$TOTAL: $PROMPT | $MODEL ==="
  uv run python analysis/reset_cards.py --all --table cards_to_analyze2
  ORACLE_FLAG=""
  if [ "$PROMPT" = "prompts/prompt8.md" ] || [ "$PROMPT" = "prompts/prompt10.md" ]; then ORACLE_FLAG="--with-oracle-text"; fi
  uv run python analysis/analyze_batch.py --prompt "$PROMPT" --model "$MODEL" --skip-existing --table cards_to_analyze2 $ORACLE_FLAG
  IDX=$((IDX + 1))
done

echo ""
echo "=== All combos complete. Generating reports... ==="

for COMBO in "${COMBOS[@]}"; do
  PROMPT=$(echo "$COMBO" | awk '{print $1}')
  MODEL=$(echo "$COMBO"  | awk '{print $2}')
  Rscript analysis/render_accuracy_report.R "$PROMPT" "$MODEL"
done

Rscript analysis/render_meta_report.R

echo ""
echo "=== Done. ==="
