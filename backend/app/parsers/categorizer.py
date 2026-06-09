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


def categorize(merchant: str, description: str) -> str:
    text = (merchant + " " + description).lower()
    for category, keywords in CATEGORY_RULES:
        if any(kw in text for kw in keywords):
            return category
    return DEFAULT_CATEGORY
