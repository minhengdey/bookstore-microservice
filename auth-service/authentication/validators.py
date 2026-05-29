def normalize_role(role: str) -> str:
    value = (role or "").strip().lower()
    if value == "manager":
        return "admin"
    if value not in ("customer", "staff", "admin"):
        raise ValueError("role must be customer, staff, or admin")
    return value


def validate_password_strength(password: str) -> None:
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
