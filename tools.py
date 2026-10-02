"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    listings = load_listings()

    # 1. Hard filters: drop anything over the price or in the wrong size.
    if max_price is not None:
        listings = [l for l in listings if l["price"] <= max_price]
    if size is not None:
        listings = [l for l in listings if _size_matches(size, l["size"])]

    # 2. No keywords to score on (e.g. the query was just "under $30"):
    #    everything that passed the filters is a match.
    query_words = _words(description)
    if not query_words:
        return listings[: config.SEARCH_RESULT_LIMIT]

    # 3. Score each listing by how many query words it contains.
    #    A word in the title counts double — it's the strongest signal.
    scored = []
    for listing in listings:
        title_words = _words(listing["title"])
        other_words = _words(" ".join([
            listing["description"],
            listing["category"],
            " ".join(listing["style_tags"]),
            " ".join(listing["colors"]),
            listing["brand"] or "",          # brand is often None
        ]))
        score = 0
        for word in query_words:
            if word in title_words:
                score += 2
            elif word in other_words:
                score += 1
        if score > 0:
            scored.append((score, listing))

    # 4. Best match first, at most SEARCH_RESULT_LIMIT of them.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [listing for _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


def _words(text: str) -> set[str]:
    """
    Lowercase words in `text`, with a trailing "s" dropped so "boots" matches
    "boot" and "tees" matches "tee".
    """
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words}


def _size_matches(wanted: str, listing_size: str) -> bool:
    """
    Whole-token size match, so "M" matches "S/M" and "M/L" but "S" does NOT
    match "US 9", and "L" does NOT match "XL" or "W30 L30".

    Listing sizes are split on "/" and spaces, with anything in brackets
    dropped: "XL (oversized)" → {"XL"}, "US 9" → {"US", "9"}.
    A leading "US" on the wanted size is ignored, so "9" and "US 9" both work.
    "One Size" items only match a request for "one size".
    """
    wanted = wanted.upper().strip()
    wanted = re.sub(r"^US\s+", "", wanted)

    cleaned = re.sub(r"\(.*?\)", "", listing_size.upper())
    if "ONE SIZE" in cleaned:
        return wanted == "ONE SIZE"
    tokens = set(re.split(r"[/\s]+", cleaned.strip()))
    return wanted in tokens


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    item_text = _describe_item(new_item)
    items = wardrobe.get("items") or []

    system = (
        "You are a friendly thrift-store stylist. Be specific and practical. "
        "Keep it under 120 words. No preamble."
    )

    if not items:
        # Empty wardrobe: there's nothing to pair with, so give general ideas
        # instead of inventing clothes the user doesn't own.
        prompt = (
            f"Someone is thinking about buying this thrifted item:\n{item_text}\n\n"
            "They haven't saved any of the clothes they own yet. Suggest one or two "
            "outfits built around this item, using common pieces most people "
            "could find easily or would already have in their collection."
        )
    else:
        wardrobe_text = "\n".join(
            f"- {w['name']} ({w['category']}; colors: {', '.join(w['colors'])})"
            for w in items
        )
        prompt = (
            f"Someone is thinking about buying this thrifted item:\n{item_text}\n\n"
            f"Here are all the items they already own:\n{wardrobe_text}\n\n"
            "Suggest one or two outfits that pair the new item with pieces from "
            "their wardrobe. Name the wardrobe pieces exactly as listed do not leave out any details."
        )

    return generate(prompt, system=system)


def _describe_item(item: dict) -> str:
    """A listing dict as a few lines of text the model can read."""
    lines = [
        f"Title: {item['title']}",
        f"Category: {item['category']}",
        f"Colors: {', '.join(item['colors'])}",
        f"Style: {', '.join(item['style_tags'])}",
        f"Condition: {item['condition']}",
        f"Price: ${item['price']:g} on {item['platform']}",
    ]
    if item.get("brand"):
        lines.append(f"Brand: {item['brand']}")
    return "\n".join(lines)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return (
            "No fit card: there was no outfit suggestion to write about. "
            "Check that suggest_outfit returned text."
        )

    system = (
        "You write short, casual social media captions about thrift finds. "
        "Sound like a real person posting, but don't be too formal or only talk about the item."
    )
    prompt = (
        f"Write a 2-4 sentence caption about this thrift find.", "Item: {new_item['title']}", "Price: ${new_item['price']:g}\n", "Platform: {new_item['platform']}\n"
        f"Style: {', '.join(new_item['style_tags'])}", "How they're planning to wear it:\n{outfit}"
        "Mention the item, the price and the platform once each. Also add a description of the the item and Be specific "
        "about the vibe. Hashtags and an emoji or two are fine."
    )
    return generate(prompt, system=system)
