Analyze each Magic: The Gathering card and categorize specified mechanics based on gameplay mechanics and strategic purposes for the commander format. The list of core mechanics to analyze is provided below. For each card, tag the card mechanics and evaluate using the tiered rating system in <card_tier>. Identify each mechanic that applies to the card and assign it a tier rating based on its power and relevance in the Commander format.

Cards to analyze are listed below.  The format is specified as `Name: card_name. Text: card_text` where card_name is the name of the card and card_text is the oracle text (i.e. the official wording) of the card.  Use the card_text to determine the mechanics and their tiers.

</task>

<mechanics>

## Mechanics

Here are key mechanics I want you to tag.  This is not a comprehensive list of mechanics, I only want you to tag these.  Use only these mechanics and do not add any new ones.

- ramp: Accelerates your mana production (Birds of Paradise, Cultivate, Sol Ring, Dockside Extortionist). Includes treasures, rituals, and other effects which increase the amount of mana you have available.  Does not include mana fixing or untapping effects.
- card_advantage: Net positive card advantage giving you access to more than one card (Harmonize, Rhystic Study, Mulldrifter).  Does not include cantrips, cycling, card selection, or tutors unless they provide net positive card advantage (i.e. they give you more than one card).
- targeted_disruption: A single card which removes or interacts with a single target opponent card (Path to Exile, Counterspell, Cyclonic Rift). Includes targeted removal, bounce spells, ability disruption, tap effects, and counterspells.
- mass_disruption: A single card which affects multiple opponent cards or multiple opponents directly (Wrath of God, Cyclonic Rift, Rest in Peace). Includes mass removal, mass bounce, graveyard hate, and tap effects.
- go_wide: Card supports a "go_wide" strategy by creating additional tokens or creates.
- anthem: increases toughness or power of all creatures in the commander deck.
- overrun: Provides buffs to (multiple) creatures strength, power, evasivenss or ability to get through, enabling a large number of creatures to do a high level of damage
</mechanics>

<card_tier>

## Tier System

Each tier rating applies only to the specific mechanic being evaluated, not the overall card power

- **S+ Tier**: Most powerful effects in the format (Sol Ring ramp, Cyclonic Rift mass_disruption)
- **S-Tier**: Extremely powerful effects (Jeska's Will ramp, Rhystic Study card_advantage, Counterspell counterspells, Swords to Plowshares targeted_disruption)
- **A-Tier**: Very strong effects (Rampant Growth ramp, Harmonize card_advantage, Beast Within targeted_disruption)
- **B-Tier**: Good effects (Mind Stone ramp, Felidar Cub targeted_disruption, Sign in Blood card_advantage)
- **C-Tier**: Moderate effects (Mulldrifter card_advantage)
- **D-Tier**: Weak effects 
</card_tier>

<analysis_instructions>
## Analysis Instructions

Step-by-Step Card Analysis:

1. Read the entire card text carefully
2. Identify ALL abilities and effects (not just the primary one)
3. Consider secondary and tertiary functions
4. Consider multiplayer context - how does this work with 2+ opponents?
5. Evaluate each ability against the mechanics list
6. Tag ALL applicable mechanics with appropriate tiers
7. Do not consider mana cost when determining tier ratings
8. Evaluate each mechanic in isolation - Rate only the specific mechanic being tagged, ignoring all other abilities on the card
9. Evaluate the tier based on the effect itself, not potential synergies or combos.  Ex. Mulldrifter is powerful card advantage in blink decks, but by itself it (a) only provides one card of advantage and (b) isn't repeatble; therefore Mulldrifter should be a C-Tier for card_advantage.

Key Reminders:

- Cards can have 2+ mechanics - don't stop at just one
- Consider both immediate and ongoing effects
- A single card can serve multiple roles (Cyclonic Rift is both targeted_disruption and mass_disruption)
- Tier ratings should reflect Commander meta relevance, not just raw power
- Consider effect power and multiplayer impact when rating
- Multiple mechanics = multiple separate evaluations - A card with ramp + card_advantage gets two separate ratings based on how good each individual effect is
</analysis_instructions>

<format>
## Format

Return your results in a json format. Return only the json output, do not include explanatory text before or after the output. Each card should be a key in the JSON object, and the value should be another JSON object with the mechanics as keys and their respective tier ratings as values.
{
    "Card Name": {
        "mechanic_1": "Tier Rating",
        "mechanic_2": "Tier Rating",
        "mechanic_3": "Tier Rating"
    }
}
</format>

<quality_control>
## Quality Control
Quality Control - MANDATORY CHECKS

Before finalizing tags, verify:

1. ✓ Read the ENTIRE card text including reminder text
2. ✓ Used ONLY approved mechanic names from the list above
3. ✓ Used exact tier names (S+ Tier, S-Tier, A-Tier, B-Tier, C-Tier, D-Tier)
4. ✓ Tagged ALL applicable mechanics - cards frequently have more than one mechanic
5. ✓ Followed the instructions in <mechanics> and <card_tier> when evaluating mechanics and tiers.
6. ✓ Considered both immediate and ongoing effects
7. ✓ Evaluated multiplayer impact for tier ratings
8. ✓ Ignored mana cost when assigning tier ratings
9. ✓ Rated each mechanic based solely on that specific effect, ignoring other abilities on the card
10. ✓ Return only the JSON output, no additional text or explanations
</quality_control>

<examples>
## Examples

Example output should look like the following: note there is no explanatory text, just the JSON output. Use the exact mechanic names specified in <mechanics> and the exact tier names specified in <card_tier>.

Note that these examples only tag for the ramp, card_advantage, targeted_disruption, and mass_disruption mechanics.  If the user enters additional mechanics, they will not be present here - you should still tag them in your result.  Example: if the user enters go_wide as a mechanic "Ranar the Ever-Watchful" should be tagged as "go_wide": "B-Tier"
<example_output>
{
   "Ranar the Ever-Watchful": {},
   "Mulldrifter": {
       "card_advantage": "C-Tier"
   },
   "Doomskar": {
       "mass_disruption": "B-Tier"
   },
   "Sol Ring": {
       "ramp": "S+ Tier"
   },
   "Arcane Signet": {
       "ramp": "A-Tier"
   },
   "Commander's Sphere": {
       "ramp": "A-Tier"
   },
   "Cyclonic Rift": {
       "mass_disruption": "S-Tier",
       "targeted_disruption": "B-Tier"
   }, 
   "Wily Bandar": {},
   "Soul Snare": {
       "targeted_disruption": "B-Tier"
   },
   "Savannah Lions": {},
   "Reprieve": {
        "targeted_disruption": "B-Tier"
   }, 
   "Propoganda": {
       "mass_disruption": "B-Tier"
   }
}
</example_output>
</examples>