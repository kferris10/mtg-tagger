# Prompts

| Prompt | Description | Built off |
|--------|-------------|-----------|
| prompt.md | Original prompt with 6 core mechanics (ramp, card_advantage, targeted/mass disruption, go_wide, anthem); no oracle text. | — |
| prompt2.md | Minor variation of prompt.md with same core mechanics. | prompt.md |
| prompt3.md | Adds explicit note that cards can qualify for both targeted_disruption and mass_disruption simultaneously. | prompt2.md |
| prompt4.md | More detailed mechanic definitions with clearer examples and boundary conditions. | prompt3.md |
| prompt5.md | Expands go_wide and anthem definitions; minor wording improvements. | prompt4.md |
| prompt6.md | Minor wording refinements. | prompt5.md |
| prompt7.md | Major expansion: adds overrun, go_tall, equipment_tutor, cheat_equip_cost, get_through, protection, etb_effects, untap_effects, blink_flicker, mana_sink, and goad; no oracle text. | prompt6.md |
| prompt8.md | Adds oracle text in input format (Card Name \| Oracle Text) to the expanded taxonomy from prompt7. | prompt7.md |
| prompt9.md | No oracle text (relies on model recall); refined exclusion rules for all mechanics; detailed Step-by-Step tagging instructions. | prompt7.md |
| prompt10.md | Oracle text input format; adds "err toward tagging" guidance for minor disruption effects; most detailed definitions. | prompt8.md |
| prompt11.md | Adds D-Tier tier anchor examples for minor effects; uses oracle text input format. | prompt10.md |
| prompt12.md | Updated mechanics definitions from mechanics.md; explicit overlapping-tag guidance; etb_effects now tagged alongside other mechanics rather than suppressed by them. | prompt9.md |
| prompt13.md | Visible recall: model writes a one-line oracle-text summary per card before the JSON (output in a fenced block); UNKNOWN/low_confidence escape hatch instead of guessing; get_through tags every natural flyer; mass_disruption includes forced-combat effects; ramp/untap verify rule; concrete etb_effects value list. | prompt12.md |
| feedback.md | Second-pass review prompt: takes initial ratings + oracle text and checks for missed mechanics, false positives, tier calibration errors, exclusion violations, and minor disruption omissions. | prompt11.md |
