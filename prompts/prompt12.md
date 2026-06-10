You will receive a list of Magic: The Gathering card names and a set of mechanics from a tagging taxonomy.
Your task is to identify which mechanics apply to each card and assign a tier rating reflecting the mechanic's power in the Commander format.

CARD_LIST_PLACEHOLDER

[Mechanics]

Tag ONLY the following mechanics. Do NOT invent new mechanic names.

Tags are not mutually exclusive. A card should receive ALL mechanic tags that apply to it. Only skip a tag when the mechanic definition below contains an explicit exclusion rule for that case.

- ramp: Increases your mana production above the curve by adding new mana sources or mana itself (Birds of Paradise, Cultivate, Sol Ring, Dockside Extortionist). Includes treasures, rituals, and other effects which increase the amount of mana you have available. Does not include mana fixing or untapping effects.
- card_advantage: Net positive card advantage giving you access to 1+ more cards than you spent to cast (Harmonize, Rhystic Study, Mulldrifter). Does not include cantrips, cycling, card selection, or tutors unless they provide net positive card advantage (i.e. they net you more cards than you spent).
- targeted_disruption: A single card which removes or interacts with a single target opponent card (Path to Exile, Counterspell, Cyclonic Rift). Includes targeted removal, bounce spells, ability disruption, tap effects, and counterspells.
- mass_disruption: A single card which affects multiple opponent cards or multiple opponents directly (Wrath of God, Cyclonic Rift, Rest in Peace). Includes mass removal, mass bounce, graveyard hate, and tap effects. Cards with both modes qualify for both targeted_disruption and mass_disruption.
- go_wide: Creates multiple creature tokens or scales token production (Raise the Alarm, Avenger of Zendikar).
- anthem: PERSISTENT static or triggered buff to power/toughness of multiple creatures you control (Glorious Anthem, tribal lords). Does NOT include one-turn combat bursts (see overrun).
- overrun: ONE-SHOT combat burst granting power, toughness, or evasion to multiple creatures for one attack (Overrun, Craterhoof Behemoth). Distinguished from anthem by being temporary. Does NOT include effects that pump attackers based on mana paid or attacker count — those are mana_sink.
- go_tall: Permanently or persistently increases a SINGLE creature's power or toughness numbers (Blackblade Reforged, Bear Umbra, Tuvasa the Sunlit). Includes auras and equipment with a static +X/+X boost or scaling growth. Does NOT include type-wide buffs (see anthem). Does NOT include indestructible or hexproof — those are protection, not go_tall.
- equipment_tutor: Searches for equipment cards (Stoneforge Mystic). Higher tier if the equipment enters the battlefield directly.
- cheat_equip_cost: Attaches equipment for free or at reduced cost (Puresteel Paladin, Sigarda's Aid).
- get_through: A creature has, or a card grants, evasion that allows dealing combat damage despite blockers: flying, trample, shadow, menace, intimidate, unblockable (Whispersilk Cloak, Trailblazer's Boots). Tag a creature if it NATURALLY has evasion as a meaningful function. Tag equipment/auras that grant evasion. Also includes effects restricting how many creatures can block (Mirri, Weatherlight Duelist). Does NOT include: (a) go_wide cards whose tokens happen to have evasion — tag go_wide; (b) double strike or first strike — combat damage bonuses, not evasion; (c) anthem effects that buff flying creatures.
- protection: A permanent cannot be Damaged, Enchanted/equipped, Blocked, or Targeted by source(s) (Lightning Greaves, Darksteel Plate, Fleecemane Lion, Jareth Leonine Titan). This is about immunity from these effects. Does NOT include: (a) blink/flicker effects — Cloudshift, Ephemerate, Momentary Blink, and Whitemane Lion are blink_flicker, NOT protection; (b) first strike, vigilance, or trample.
- etb_effects: An ETB (enters-the-battlefield) trigger that generates meaningful value (Mulldrifter draws cards, Acidic Slime destroys a permanent, Whitemane Lion returns a creature). Tag whenever the ETB provides meaningful value, even if that value is also captured by another mechanic — a creature that draws a card on ETB gets both etb_effects and card_advantage.
- untap_effects: Untaps permanents to generate extra mana or enable repeated abilities (Seedborn Muse, Wilderness Reclamation). Higher tier for untapping multiple permanents or untapping on each opponent's turn.
- blink_flicker: Temporarily exiles and returns a permanent to trigger ETB abilities (Conjurer's Closet, Ephemerate, Teleportation Circle).
- mana_sink: Productively consumes extra mana beyond the card's casting cost. Includes: (1) X-cost spells that scale with mana (Martial Coup, Commander's Insight); (2) repeatable activated abilities that convert mana into value (Jazal Goldmane, Kemba Kha Enduring, Leafdrake Roost, Temur Sabertooth). The defining trait: extra mana always has a productive outlet.
- goad: Forces opponent creatures to attack each combat, and goaded creatures cannot attack the goading player (Marisi Breaker of the Coil, Disrupt Decorum). Higher tier for multiple or repeatable goad.

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
