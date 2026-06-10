You will receive a list of Magic: The Gathering card names and a set of mechanics from a tagging taxonomy.
Your task is to identify which mechanics apply to each card and assign a tier rating reflecting the mechanic's power in the Commander format.

CARD_LIST_PLACEHOLDER

[Mechanics]

Tag ONLY the following mechanics. Do NOT invent new mechanic names.

Tags are not mutually exclusive. A card should receive ALL mechanic tags that apply to it. Only skip a tag when the mechanic definition below contains an explicit exclusion rule for that case.

MECHANICS_PLACEHOLDER

[Tier Anchors]

Rate each mechanic based ONLY on that mechanic's effect in Commander, ignoring mana cost and other abilities on the card.

- S+ Tier: Format-defining (Sol Ring ramp, Cyclonic Rift mass_disruption, Seedborn Muse untap_effects)
- S-Tier: Extremely powerful (Jeska's Will ramp, Rhystic Study card_advantage, Swords to Plowshares targeted_disruption)
- A-Tier: Very strong (Rampant Growth ramp, Harmonize card_advantage, Beast Within targeted_disruption, Darksteel Plate protection, Teleportation Circle blink_flicker, Blackblade Reforged go_tall, Staff of Domination mana_sink, Overrun overrun)
- B-Tier: Good (Mind Stone ramp, Sign in Blood card_advantage, Swiftfoot Boots protection, Lightning Greaves protection, Conjurer's Closet blink_flicker, Bear Umbra go_tall, Jazal Goldmane mana_sink, Glorious Anthem anthem)
- C-Tier: Moderate (Mulldrifter card_advantage, Whispersilk Cloak get_through, Ephemerate blink_flicker, minor +1/+1 aura go_tall, totem armor protection)
- D-Tier: Weak or marginal effects

[Examples]

Tag only the mechanics listed above. Cards with no applicable mechanics get an empty object.

{
   "Sol Ring": { "ramp": "S+ Tier" },
   "Mulldrifter": { "card_advantage": "C-Tier", "etb_effects": "C-Tier" },
   "Cyclonic Rift": { "mass_disruption": "S-Tier", "targeted_disruption": "B-Tier" },
   "Ranar the Ever-Watchful": { "go_wide": "B-Tier", "blink_flicker": "C-Tier" },
   "Doomskar": { "mass_disruption": "B-Tier" },
   "Arcane Signet": { "ramp": "A-Tier" },
   "Acidic Slime": { "targeted_disruption": "B-Tier", "etb_effects": "B-Tier" },
   "Wily Bandar": {},
   "Savannah Lions": {},
   "Propaganda": { "mass_disruption": "B-Tier" }
}

[Instructions]

Step 1: For each card name, internally recall the card's complete oracle text from your training knowledge before assigning any tags — every word, every ability, every triggered effect. Do not rely on a vague impression of what the card does; work from the actual oracle text. Identify ALL abilities from that text — primary, secondary, and triggered. If you cannot confidently recall a card's oracle text, rely only on its broadly known gameplay function.

Step 2: For each ability, perform ONE of the following:
1. If the ability matches a mechanic in [Mechanics], tag it with the appropriate tier from [Tier Anchors] and continue to the next ability.
2. If the ability partially matches a mechanic but an explicit exclusion rule in [Mechanics] applies, do NOT tag it and continue.
3. If the ability does not match any mechanic, skip it.

Step 3: Before outputting, verify:
- Used ONLY mechanic names from [Mechanics] — the evasion mechanic is "get_through" (NOT "go_through")
- Did NOT tag blink/flicker spells as protection
- Did NOT tag go_tall for cards that grant indestructible/hexproof — use protection
- Did NOT tag get_through for go_wide cards whose tokens have evasion
- DID tag etb_effects alongside other overlapping mechanics — if an ETB draws cards, tag both etb_effects AND card_advantage
- Used exact tier names: S+ Tier, S-Tier, A-Tier, B-Tier, C-Tier, D-Tier

Output: JSON only, no explanatory text. Each card is a key; its value is an object of mechanic: tier pairs.
