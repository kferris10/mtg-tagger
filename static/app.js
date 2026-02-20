// ─── User-visible strings ───────────────────────────────────────────────────
const STRINGS = {
    noMechanics:      "No tagged mechanics",
    rawJsonShow:      "Show raw JSON",
    rawJsonHide:      "Hide raw JSON",
    searchPlaceholder: "Search cards...",
    clearFilters:     "Clear filters",
    showingXofY:      (n, total) => `Showing ${n} of ${total} results`,
    noCardsMatch:     "No cards match your filters",
    clearAllFilters:  "Clear all filters",
    noTaggedCount:    (n) => `${n} card${n === 1 ? '' : 's'} had no tagged mechanics`,
    selectCard:       "Select a card...",
    tierListNoMatch:  "No cards match your filters",
    validationNoCards: "Please enter card data.",
    accessDenied:     "Access denied: incorrect access code.",
    unexpectedError:  "An unexpected error occurred.",
    renderError:      "Error rendering results: ",
    networkError:     "Network error: could not reach the server.",
    mechanicsFallback: '- ramp: Accelerates your mana production...\n- card_advantage: Net positive card advantage...',
};
// ────────────────────────────────────────────────────────────────────────────

const btn = document.getElementById("submit-btn");
const loading = document.getElementById("loading");
const errorEl = document.getElementById("error");
const errorMsg = document.getElementById("error-msg");
const errorDismiss = document.getElementById("error-dismiss");
const resultsEl = document.getElementById("results");
const resultsContent = document.getElementById("results-content");
const resultsTable = document.getElementById("results-table");
const rawToggle = document.getElementById("raw-toggle");
const rawJson = document.getElementById("raw-json");
const rightPanel = document.getElementById("right-panel");
const emptyState = document.getElementById("empty-state");

const cardDetail = document.getElementById("card-detail");
const cardSelect = document.getElementById("card-select");
const cardRatings = document.getElementById("card-ratings");

let errorTimer = null;
let lastResult = null;

// View state
let currentView = "tierlist";
let lastRows = [];
let noMechCountGlobal = 0;
let renderTableFn = null;
let renderFiltersFn = null;
const scryfallCache = {};
const scryfallQueue = [];
let scryfallRunning = false;

// Filter state
const filterState = {
    mechanics: new Set(),
    tiers: new Set(),
    searchText: ""
};

function hasActiveFilters() {
    return filterState.mechanics.size > 0 ||
           filterState.tiers.size > 0 ||
           filterState.searchText.trim() !== "";
}

function applyFilters(rows) {
    if (!hasActiveFilters()) {
        return rows;
    }

    return rows.filter(row => {
        // Mechanic filter (OR logic within mechanics)
        const mechMatch = filterState.mechanics.size === 0 ||
                         filterState.mechanics.has(row.mechanic);

        // Tier filter (OR logic within tiers)
        const tierMatch = filterState.tiers.size === 0 ||
                         filterState.tiers.has(row.tierRankVal);

        // Search filter (AND logic for card name)
        const searchMatch = filterState.searchText === "" ||
                           row.card.toLowerCase().includes(
                               filterState.searchText.toLowerCase()
                           );

        // Combine with AND logic between filter types
        return mechMatch && tierMatch && searchMatch;
    });
}

function clearAllFilters() {
    filterState.mechanics.clear();
    filterState.tiers.clear();
    filterState.searchText = "";
    const searchInput = document.getElementById("card-search");
    if (searchInput) searchInput.value = "";
}

function switchView(view) {
    currentView = view;
    document.getElementById("tab-table").classList.toggle("active", view === "table");
    document.getElementById("tab-tierlist").classList.toggle("active", view === "tierlist");
    document.getElementById("results-table").style.display = view === "table" ? "" : "none";
    document.getElementById("results-tierlist").style.display = view === "tierlist" ? "" : "none";
    renderActiveView();
}

function renderActiveView() {
    if (currentView === "table" && renderTableFn) renderTableFn();
    else if (currentView === "tierlist" && lastRows.length > 0) renderTierList();
}

// Generate display label from mechanic key
function formatMechanicLabel(mechKey) {
    // Use predefined label if exists, otherwise format the key
    const PREDEFINED_LABELS = {
        ramp: "Ramp",
        card_advantage: "Card Advantage",
        targeted_disruption: "Targeted Disruption",
        mass_disruption: "Mass Disruption",
        go_wide: "Go Wide",
        anthem: "Anthem",
        overrun: "Overrun"
    };

    if (PREDEFINED_LABELS[mechKey]) {
        return PREDEFINED_LABELS[mechKey];
    }

    // Fallback: convert snake_case to Title Case
    return mechKey
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

function renderCardDetail(cardName) {
    const mechanics = lastResult[cardName];
    if (!mechanics) { cardRatings.innerHTML = ""; return; }
    const entries = Object.entries(mechanics);
    if (entries.length === 0) {
        cardRatings.innerHTML = `<p class="card-no-mechanics">${STRINGS.noMechanics}</p>`;
        return;
    }
    let html = "";
    for (const [mech, tier] of entries) {
        const label = formatMechanicLabel(mech);
        const cls = tierBadgeClass(tier);
        html += `<div class="card-rating-row"><span>${esc(label)}</span><span class="badge ${cls}">${esc(tier)}</span></div>`;
    }
    cardRatings.innerHTML = html;
}

cardSelect.addEventListener("change", () => {
    if (cardSelect.value) renderCardDetail(cardSelect.value);
    else cardRatings.innerHTML = "";
});

rawToggle.addEventListener("click", () => {
    rawJson.classList.toggle("visible");
    rawToggle.textContent = rawJson.classList.contains("visible")
        ? STRINGS.rawJsonHide : STRINGS.rawJsonShow;
});

function dismissError() {
    errorEl.classList.remove("visible");
    if (errorTimer) { clearTimeout(errorTimer); errorTimer = null; }
}

errorDismiss.addEventListener("click", dismissError);
errorEl.addEventListener("click", dismissError);

function esc(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
}

function tierBadgeClass(tier) {
    const t = tier.toLowerCase();
    if (t.startsWith("s"))  return "badge-s";
    if (t.startsWith("a"))  return "badge-a";
    if (t.startsWith("b"))  return "badge-b";
    if (t.startsWith("c"))  return "badge-c";
    if (t.startsWith("d"))  return "badge-d";
    return "badge-c";
}

function tierRank(tier) {
    const t = tier.toLowerCase().replace(/[- ]?tier$/i, "").trim();
    const ranks = {"s+": 0, "s": 1, "a": 2, "b": 3, "c": 4, "d": 5};
    return ranks[t] !== undefined ? ranks[t] : 6;
}

function renderResults(data) {
    // Reset filters when new data arrives
    clearAllFilters();

    // If the API returned a plain string, show it as raw text
    if (typeof data === "string") {
        try {
            data = JSON.parse(data);
        } catch {
            resultsTable.innerHTML = `<pre>${data}</pre>`;
            resultsContent.textContent = data;
            rawJson.classList.remove("visible");
            rawToggle.textContent = STRINGS.rawJsonShow;
            return;
        }
    }
    const result = data;

    // Build flat rows array
    const rows = [];
    let noMechCount = 0;
    for (const [cardName, mechanics] of Object.entries(result)) {
        const mechEntries = Object.entries(mechanics);
        if (mechEntries.length === 0) {
            noMechCount++;
        } else {
            for (const [mech, tier] of mechEntries) {
                rows.push({
                    card: cardName,
                    mechanic: mech,
                    mechanicLabel: formatMechanicLabel(mech),
                    tier: tier,
                    tierRankVal: tierRank(tier)
                });
            }
        }
    }
    lastRows = rows;
    noMechCountGlobal = noMechCount;

    // Category counts with mechanic key mapping
    const counts = {};
    const mechanicKeyMap = {}; // Map label → key
    for (const row of rows) {
        counts[row.mechanicLabel] = (counts[row.mechanicLabel] || 0) + 1;
        mechanicKeyMap[row.mechanicLabel] = row.mechanic;
    }
    const countsSorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);

    // Sort state
    let sortCol = "tier";
    let sortAsc = true; // ascending tierRank = strongest first

    function renderFilters() {
        const filtersEl = document.getElementById("results-filters");
        const filteredRows = applyFilters(rows);

        // Filter header with search and clear button
        let html = '<div class="filter-header">';
        html += `<input type="text" id="card-search" class="card-search" placeholder="${STRINGS.searchPlaceholder}">`;
        html += `<button id="clear-filters" class="clear-filters-btn" style="display: ${hasActiveFilters() ? 'inline-block' : 'none'}">${STRINGS.clearFilters}</button>`;
        html += '</div>';

        // Category counts
        html += '<div class="category-counts">';
        for (const [label, count] of countsSorted) {
            const mechKey = mechanicKeyMap[label];
            const isActive = filterState.mechanics.has(mechKey);
            html += `<span class="count-chip${isActive ? ' active' : ''}" data-mechanic="${esc(mechKey)}">${esc(label)}: ${count}</span>`;
        }

        // Tier filters
        html += '<div class="tier-filters"><span class="tier-label">Tiers:</span>';
        const tiers = [
            {rank: 0, label: 'S+', class: 'badge-s'},
            {rank: 1, label: 'S',  class: 'badge-s'},
            {rank: 2, label: 'A',  class: 'badge-a'},
            {rank: 3, label: 'B',  class: 'badge-b'},
            {rank: 4, label: 'C',  class: 'badge-c'},
            {rank: 5, label: 'D',  class: 'badge-d'}
        ];
        for (const tier of tiers) {
            const isActive = filterState.tiers.has(tier.rank);
            html += `<span class="badge tier-filter ${tier.class}${isActive ? ' active' : ''}" data-tier="${tier.rank}">${tier.label}</span>`;
        }
        html += '</div></div>'; // tier-filters, category-counts

        if (hasActiveFilters() && filteredRows.length < rows.length) {
            html += `<p class="filter-info">${STRINGS.showingXofY(filteredRows.length, rows.length)}</p>`;
        }

        filtersEl.innerHTML = html;
        attachFilterHandlers();
    }

    function renderTable() {
        const filteredRows = applyFilters(rows);
        filteredRows.sort((a, b) => {
            let cmp = 0;
            if (sortCol === "card") {
                cmp = a.card.localeCompare(b.card);
            } else if (sortCol === "mechanic") {
                cmp = a.mechanicLabel.localeCompare(b.mechanicLabel);
            } else {
                cmp = a.tierRankVal - b.tierRankVal;
            }
            return sortAsc ? cmp : -cmp;
        });

        const arrow = sortAsc ? "▲" : "▼";
        const thCard = `Card${sortCol === "card" ? ' <span class="sort-arrow">' + arrow + '</span>' : ''}`;
        const thMech = `Mechanic${sortCol === "mechanic" ? ' <span class="sort-arrow">' + arrow + '</span>' : ''}`;
        const thTier = `Tier${sortCol === "tier" ? ' <span class="sort-arrow">' + arrow + '</span>' : ''}`;

        if (filteredRows.length === 0 && hasActiveFilters()) {
            resultsTable.innerHTML = `<div class="empty-filter-state"><p>${STRINGS.noCardsMatch}</p><button id="clear-filters-empty">${STRINGS.clearAllFilters}</button></div>`;
            const clearEmptyBtn = document.getElementById("clear-filters-empty");
            if (clearEmptyBtn) {
                clearEmptyBtn.addEventListener("click", () => {
                    clearAllFilters();
                    renderFilters();
                    renderActiveView();
                });
            }
            return;
        }

        let html = '<table class="results-table"><thead><tr>';
        html += `<th class="sort-header" data-col="card">${thCard}</th>`;
        html += `<th class="sort-header" data-col="mechanic">${thMech}</th>`;
        html += `<th class="sort-header" data-col="tier">${thTier}</th>`;
        html += '</tr></thead><tbody>';
        for (const row of filteredRows) {
            const cls = tierBadgeClass(row.tier);
            html += `<tr><td>${esc(row.card)}</td><td>${esc(row.mechanicLabel)}</td><td><span class="badge ${cls}">${esc(row.tier)}</span></td></tr>`;
        }
        html += '</tbody></table>';
        if (noMechCount > 0) {
            html += `<p class="muted">${STRINGS.noTaggedCount(noMechCount)}</p>`;
        }

        resultsTable.innerHTML = html;
        resultsTable.querySelectorAll(".sort-header").forEach(th => {
            th.addEventListener("click", () => {
                const col = th.getAttribute("data-col");
                if (sortCol === col) { sortAsc = !sortAsc; } else { sortCol = col; sortAsc = true; }
                renderTable();
            });
        });
    }

    renderTableFn = renderTable;
    renderFiltersFn = renderFilters;

    function attachFilterHandlers() {
        const searchInput = document.getElementById("card-search");
        if (searchInput) {
            searchInput.value = filterState.searchText;
            searchInput.addEventListener("input", (e) => {
                filterState.searchText = e.target.value.trim();
                renderFilters();
                renderActiveView();
            });
        }

        const clearBtn = document.getElementById("clear-filters");
        if (clearBtn) {
            clearBtn.addEventListener("click", () => {
                clearAllFilters();
                renderFilters();
                renderActiveView();
            });
        }

        document.querySelectorAll(".count-chip").forEach(chip => {
            chip.addEventListener("click", () => {
                const mechanic = chip.getAttribute("data-mechanic");
                if (filterState.mechanics.has(mechanic)) { filterState.mechanics.delete(mechanic); }
                else { filterState.mechanics.add(mechanic); }
                renderFilters();
                renderActiveView();
            });
        });

        document.querySelectorAll(".tier-filter").forEach(badge => {
            badge.addEventListener("click", () => {
                const tier = parseInt(badge.getAttribute("data-tier"));
                if (filterState.tiers.has(tier)) { filterState.tiers.delete(tier); }
                else { filterState.tiers.add(tier); }
                renderFilters();
                renderActiveView();
            });
        });
    }

    renderFilters();
    switchView("tierlist");

    // Raw JSON
    resultsContent.textContent = JSON.stringify(result, null, 2);
    rawJson.classList.remove("visible");
    rawToggle.textContent = STRINGS.rawJsonShow;

    // Card detail panel
    lastResult = result;
    const cardNames = Object.keys(result);
    cardSelect.innerHTML = `<option value="">${STRINGS.selectCard}</option>`;
    for (const name of cardNames) {
        cardSelect.innerHTML += `<option value="${esc(name)}">${esc(name)}</option>`;
    }
    if (cardNames.length > 0) {
        cardSelect.value = cardNames[0];
        renderCardDetail(cardNames[0]);
    }
    cardDetail.classList.add("visible");
}

// Scryfall art fetch with rate-limited queue
async function fetchArtCrop(cardName) {
    const key = cardName.toLowerCase();
    if (key in scryfallCache) return scryfallCache[key];
    return new Promise((resolve) => {
        scryfallQueue.push({ cardName, key, resolve });
        if (!scryfallRunning) runScryfallQueue();
    });
}

async function runScryfallQueue() {
    scryfallRunning = true;
    while (scryfallQueue.length > 0) {
        const { cardName, key, resolve } = scryfallQueue.shift();
        if (key in scryfallCache) { resolve(scryfallCache[key]); continue; }
        try {
            const res = await fetch(`https://api.scryfall.com/cards/named?fuzzy=${encodeURIComponent(cardName)}`);
            const artUrl = res.ok ? (await res.json()).image_uris?.art_crop ?? null : null;
            scryfallCache[key] = artUrl;
            resolve(artUrl);
        } catch {
            scryfallCache[key] = null;
            resolve(null);
        }
        await new Promise(r => setTimeout(r, 100));
    }
    scryfallRunning = false;
}

function renderTierList() {
    const TIER_DEFS = [
        { rank: 0, label: "S+", badgeClass: "badge-s" },
        { rank: 1, label: "S",  badgeClass: "badge-s" },
        { rank: 2, label: "A",  badgeClass: "badge-a" },
        { rank: 3, label: "B",  badgeClass: "badge-b" },
        { rank: 4, label: "C",  badgeClass: "badge-c" },
        { rank: 5, label: "D",  badgeClass: "badge-d" },
    ];

    const tierListEl = document.getElementById("results-tierlist");
    const filteredRows = applyFilters(lastRows);

    if (filteredRows.length === 0 && hasActiveFilters()) {
        tierListEl.innerHTML = `<div class="empty-filter-state"><p>${STRINGS.tierListNoMatch}</p></div>`;
        return;
    }

    // Group filtered rows by tier rank
    const byTier = {};
    for (const row of filteredRows) {
        if (!byTier[row.tierRankVal]) byTier[row.tierRankVal] = [];
        byTier[row.tierRankVal].push(row);
    }

    let html = '<div class="tierlist">';
    for (const td of TIER_DEFS) {
        const tierRows = byTier[td.rank];
        if (!tierRows || tierRows.length === 0) continue;
        html += `<div class="tier-row">`;
        html += `<div class="tier-row-label ${td.badgeClass}">${esc(td.label)}</div>`;
        html += `<div class="tier-row-tiles">`;
        tierRows.forEach((row, i) => {
            const escapedName = esc(row.card);
            html += `<div class="card-tile" id="tile-${td.rank}-${i}">`;
            html += `<div class="card-tile-art" data-card="${escapedName}">`;
            html += `<div class="tile-spinner"></div>`;
            html += `</div>`;
            html += `<div class="card-tile-name">${escapedName}</div>`;
            html += `<div class="card-tile-mechanic">${esc(row.mechanicLabel)}</div>`;
            html += `</div>`;
        });
        html += `</div></div>`;
    }
    if (noMechCountGlobal > 0) {
        html += `<p class="muted" style="margin-top:0.5rem">${STRINGS.noTaggedCount(noMechCountGlobal)}</p>`;
    }
    html += '</div>';
    tierListEl.innerHTML = html;

    // Fetch art crops — unique card names from visible tiles
    const seen = new Set();
    for (const row of filteredRows) {
        if (seen.has(row.card)) continue;
        seen.add(row.card);
        const cardName = row.card;
        fetchArtCrop(cardName).then(artUrl => {
            const escapedName = esc(cardName);
            const artEls = tierListEl.querySelectorAll(`[data-card="${escapedName}"]`);
            artEls.forEach(el => {
                if (artUrl) {
                    el.innerHTML = `<img class="card-tile-img" src="${artUrl}" alt="${escapedName}" loading="lazy">`;
                } else {
                    el.innerHTML = `<div class="card-tile-placeholder"></div>`;
                }
            });
        });
    }
}

btn.addEventListener("click", async () => {
    const cardData = document.getElementById("card-data").value.trim();
    const accessCode = document.getElementById("access-code").value.trim();
    const mechanics = document.getElementById("mechanics").value.trim();

    if (!cardData) {
        showError(STRINGS.validationNoCards);
        return;
    }

    btn.disabled = true;
    loading.classList.add("visible");
    rightPanel.classList.add("loading");
    dismissError();
    resultsEl.classList.remove("visible");

    const body = {
        card_data: cardData,
        access_code: accessCode || undefined,
        mechanics: mechanics || undefined
    };

    try {
        const res = await fetch("/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

        const data = await res.json();

        if (!res.ok) {
            if (res.status === 403) {
                localStorage.removeItem("mtg_tagger_access_code");
                showError(data.error || STRINGS.accessDenied);
                document.getElementById("access-code").focus();
                return;
            }
            showError(data.error || STRINGS.unexpectedError);
            return;
        }

        if (accessCode) {
            localStorage.setItem("mtg_tagger_access_code", accessCode);
        }

        emptyState.classList.add("hidden");
        renderResults(data.result);
        resultsEl.classList.add("visible");
    } catch (e) {
        if (e instanceof TypeError || e instanceof SyntaxError) {
            showError(STRINGS.renderError + e.message);
        } else {
            showError(STRINGS.networkError);
        }
    } finally {
        btn.disabled = false;
        loading.classList.remove("visible");
        rightPanel.classList.remove("loading");
    }
});

function showError(msg) {
    errorMsg.textContent = msg;
    errorEl.classList.add("visible");
    if (errorTimer) clearTimeout(errorTimer);
    errorTimer = setTimeout(() => {
        errorEl.classList.remove("visible");
        errorTimer = null;
    }, 5000);
}

// Load default mechanics on page load
async function loadDefaultMechanics() {
    try {
        const res = await fetch('/api/default-mechanics');
        const data = await res.json();
        document.getElementById('mechanics').value = data.mechanics;
    } catch (e) {
        console.error('Failed to load default mechanics:', e);
        // Fallback: set a basic default in the textarea
        document.getElementById('mechanics').placeholder = STRINGS.mechanicsFallback;
    }
}

// Default card list
const DEFAULT_CARDS = `1 Adorned Pouncer
1 Angelic Cub
1 Arahbo, Roar of the World
1 Arahbo, the First Fang
1 Arcane Signet
1 Austere Command
1 Blackblade Reforged
1 Bloodforged Battle-Axe
1 Bronzehide Lion
1 Buried Ruin
1 Canopy Vista
1 Command Tower
1 Conjurer's Mantle
1 Dawn of a New Age
1 Enlightened Ascetic
1 Entish Restoration
1 Evolving Wilds
1 Felidar Cub
1 Felidar Retreat
1 Feline Sovereign
1 Fleecemane Lion
1 Folk Hero
11 Forest
1 Harvest Season
1 Herd Heirloom
1 Horn of the Mark
1 Hunter's Insight
1 Hunter's Prowess
1 Jazal Goldmane
1 Kaheera, the Orphanguard
1 Keen Sense
1 Keeper of Fables
1 King of the Pride
1 Krosan Verge
1 Kutzil, Malamet Exemplar
1 Leonin Relic-Warder
1 Leonin Skyhunter
1 Leonin Vanguard
1 Lion Sash
1 Loam Lion
1 Mirari's Wake
1 Mirri, Weatherlight Duelist
1 Mosswort Bridge
1 Myriad Landscape
1 Nissa's Pilgrimage
1 Patchwork Banner
1 Path of Ancestry
15 Plains
1 Qasali Ambusher
1 Qasali Pridemage
1 Qasali Slingers
1 Rampant Growth
1 Reprieve
1 Rogue's Passage
1 Rout
1 Sacred Cat
1 Savannah Lions
1 Scythe Leopard
1 Selesnya Sanctuary
1 Sixth Sense
1 Sol Ring
1 Soul's Majesty
1 Stalking Leonin
1 Steppe Lynx
1 Stirring Wildwood
1 Storm of Souls
1 Sword of the Animist
1 Sword of Vengeance
1 Terramorphic Expanse
1 Thought Vessel
1 Trained Caracal
1 Traverse the Outlands
1 White Sun's Zenith
1 Whitemane Lion
1 Wild Growth
1 Wily Bandar`;

document.getElementById("card-data").value = DEFAULT_CARDS;

// Call on page load
loadDefaultMechanics();

const savedCode = localStorage.getItem("mtg_tagger_access_code");
if (savedCode) {
    document.getElementById("access-code").value = savedCode;
}

document.getElementById("tab-table").addEventListener("click", () => switchView("table"));
document.getElementById("tab-tierlist").addEventListener("click", () => switchView("tierlist"));
