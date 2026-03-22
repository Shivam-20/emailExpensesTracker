"""config/category_map.py — Built-in keyword → category mapping."""

CATEGORY_MAP: dict[str, str] = {
    # Shopping
    "amazon":        "Shopping",
    "flipkart":      "Shopping",
    "myntra":        "Shopping",
    "meesho":        "Shopping",
    "snapdeal":      "Shopping",
    "nykaa":         "Shopping",
    "ajio":          "Shopping",
    "tata cliq":     "Shopping",
    "reliance smart":"Shopping",
    "big basket":    "Shopping",
    "dmart":         "Shopping",

    # Food
    "zomato":        "Food",
    "swiggy":        "Food",
    "dominos":       "Food",
    "pizza":         "Food",
    "mcdonalds":     "Food",
    "blinkit":       "Food",
    "zepto":         "Food",
    "instamart":     "Food",
    "restaurant":    "Food",
    "dunzo":         "Food",

    # Transport
    "uber":          "Transport",
    "ola":           "Transport",
    "rapido":        "Transport",
    "metro":         "Transport",
    "redbus":        "Transport",
    "abhibus":       "Transport",

    # Subscriptions
    "netflix":           "Subscriptions",
    "spotify":           "Subscriptions",
    "hotstar":           "Subscriptions",
    "prime video":       "Subscriptions",
    "youtube premium":   "Subscriptions",
    "zee5":              "Subscriptions",
    "apple":             "Subscriptions",
    "google one":        "Subscriptions",
    "linkedin":          "Subscriptions",
    "github":            "Subscriptions",
    "adobe":             "Subscriptions",
    "microsoft 365":     "Subscriptions",

    # Utilities
    "electricity":   "Utilities",
    "bescom":        "Utilities",
    "msedcl":        "Utilities",
    "tata power":    "Utilities",
    "water bill":    "Utilities",
    "gas":           "Utilities",

    # Telecom
    "airtel":        "Telecom",
    "jio":           "Telecom",
    "vi ":           "Telecom",
    "vodafone":      "Telecom",
    "bsnl":          "Telecom",
    "recharge":      "Telecom",

    # Healthcare
    "hospital":      "Healthcare",
    "pharmacy":      "Healthcare",
    "apollo":        "Healthcare",
    "medplus":       "Healthcare",
    "1mg":           "Healthcare",
    "netmeds":       "Healthcare",
    "clinic":        "Healthcare",
    "practo":        "Healthcare",

    # Travel
    "irctc":         "Travel",
    "makemytrip":    "Travel",
    "goibibo":       "Travel",
    "yatra":         "Travel",
    "hotel":         "Travel",
    "oyo":           "Travel",
    "booking.com":   "Travel",
    "airbnb":        "Travel",
    "indigo":        "Travel",
    "airindia":      "Travel",
    "spicejet":      "Travel",
    "vistara":       "Travel",

    # Insurance
    "insurance":     "Insurance",
    "lic":           "Insurance",
    "hdfc life":     "Insurance",
    "icici prudential": "Insurance",
    "bajaj allianz": "Insurance",

    # Finance
    "emi":           "Finance",
    "loan":          "Finance",
    "credit card":   "Finance",
    "bank statement":"Finance",
    "neft":          "Finance",
    "imps":          "Finance",
    "upi":           "Finance",
}

ALL_CATEGORIES = sorted({
    "Shopping", "Food", "Transport", "Subscriptions",
    "Utilities", "Telecom", "Healthcare", "Travel",
    "Insurance", "Finance", "Other",
})
