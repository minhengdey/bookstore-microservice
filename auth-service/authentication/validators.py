def normalize_role(role: str) -> str:
    value = (role or "").strip().upper()
    if value == "MANAGER":
        return "ADMIN"
    if value not in ("CUSTOMER", "SELLER", "STAFF", "ADMIN", "SUPER_ADMIN"):
        raise ValueError("role must be CUSTOMER, SELLER, STAFF, ADMIN, or SUPER_ADMIN")
    return value

def validate_password_strength(password: str) -> None:
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
