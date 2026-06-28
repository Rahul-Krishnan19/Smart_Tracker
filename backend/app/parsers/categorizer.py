"""
Auto-categorizer based on merchant name and VPA/description keywords.
Add more keywords as you encounter new merchants.
"""

CATEGORY_RULES = [
    ("Rent",          ["rent", "lease", "housing", "pg ", "paying guest", "landlord"]),
    ("Groceries",     ["grocery", "groceries", "supermarket", "bigbasket", "blinkit", "zepto",
                       "dmart", "reliance fresh", "more retail", "star bazaar", "nature basket",
                       "spencers", "lulu", "hyper"]),
    ("Food & Dining", ["swiggy", "zomato", "dunzo", "eatsure", "faasos", "rebel foods",
                       "dominos", "pizza", "mcdonald", "kfc", "burger king", "subway",
                       "restaurant", "cafe", "coffee", "chai", "food", "hotel", "bakery",
                       "biryani", "dhaba", "canteen"]),
    ("Transport",     ["rapido", "uber", "ola", "meru", "metro", "irctc", "railway", "train",
                       "bus", "redbus", "makemytrip", "goibibo", "indigo", "spicejet", "airindia",
                       "vistara", "petrol", "fuel", "hp ", "indian oil", "bharat petroleum",
                       "fastag", "toll", "parking"]),
    ("Shopping",      ["amazon", "flipkart", "myntra", "ajio", "nykaa", "meesho", "snapdeal",
                       "shopify", "retail", "shop", "store", "mart", "mall", "decathlon",
                       "ikea", "h&m", "zara", "westside"]),
    ("Electricity",   ["electricity", "bescom", "msedcl", "tpddl", "cesc", "bses", "tneb",
                       "power", "energy", "wesco", "jvvnl", "torrent power"]),
    ("Healthcare",    ["apollo", "fortis", "medplus", "netmeds", "1mg", "pharmeasy", "doctor",
                       "clinic", "hospital", "pharmacy", "medical", "health", "lab ", "diagnostic",
                       "dentist", "optician"]),
    ("Entertainment", ["netflix", "hotstar", "primevideo", "spotify", "youtube", "zee5",
                       "sonyliv", "jiocinema", "bookmyshow", "pvr", "inox", "multiplex",
                       "gaming", "steam", "playstation"]),
]

DEFAULT_CATEGORY = "Others"

# Fixed set of valid categories the LLM is allowed to choose from. Kept in sync
# with CATEGORY_RULES above plus the default.
VALID_CATEGORIES = [
    "Rent",
    "Groceries",
    "Food & Dining",
    "Transport",
    "Shopping",
    "Electricity",
    "Healthcare",
    "Entertainment",
    "Others",
]
_VALID_LOOKUP = {c.lower(): c for c in VALID_CATEGORIES}

# Session-scoped cache keyed on merchant.lower() so we never ask the LLM twice
# for the same merchant within a process lifetime.
_llm_cache: dict[str, str] = {}

_LLM_PROMPT_TEMPLATE = """You are categorizing a bank transaction.

Merchant: {merchant}
Description: {description}

Choose the single best category from this exact list:
{categories}

Respond with ONLY the category name, exactly as written above, nothing else."""


def _categorize_with_llm(merchant: str, description: str) -> str:
    """Ask Gemini for a category when keyword matching falls through to Others.

    Results are cached per merchant. Any failure falls back to DEFAULT_CATEGORY.
    """
    cache_key = (merchant or "").strip().lower()
    if cache_key and cache_key in _llm_cache:
        return _llm_cache[cache_key]

    # Imported lazily so importing the categorizer never requires the LLM stack.
    from app.agents.llm_client import ask_text

    prompt = _LLM_PROMPT_TEMPLATE.format(
        merchant=merchant or "(unknown)",
        description=description or "(none)",
        categories="\n".join(f"- {c}" for c in VALID_CATEGORIES),
    )

    answer = ask_text(prompt)
    category = DEFAULT_CATEGORY
    if answer:
        # Normalize the model's reply against the valid set.
        category = _VALID_LOOKUP.get(answer.strip().lower(), DEFAULT_CATEGORY)

    if cache_key:
        _llm_cache[cache_key] = category
    return category


def categorize(merchant: str, description: str) -> str:
    text = (merchant + " " + description).lower()
    for category, keywords in CATEGORY_RULES:
        if any(kw in text for kw in keywords):
            return category

    # Keyword matching failed — defer to the LLM fallback (Agent 2).
    return _categorize_with_llm(merchant, description)
