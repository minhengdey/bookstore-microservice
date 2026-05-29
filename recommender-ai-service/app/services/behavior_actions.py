DEFAULT_ACTION_WEIGHTS = {
    "search": 0.4,
    "view": 1.0,
    "click": 1.5,
    "wishlist": 2.0,
    "add_to_cart": 3.0,
    "remove_from_cart": -1.0,
    "purchase": 5.0,
    "review": 2.5,
}


def normalize_action(action: str | None) -> str:
    normalized = (action or "").strip().lower()
    aliases = {
        "cart_add": "add_to_cart",
        "add-cart": "add_to_cart",
        "add_cart": "add_to_cart",
        "remove-cart": "remove_from_cart",
        "remove_cart": "remove_from_cart",
    }
    return aliases.get(normalized, normalized)
