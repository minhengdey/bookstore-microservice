import re
from rest_framework.exceptions import ValidationError

def validate_phone(value):
    if value and not re.match(r"^\+?1?\d{9,15}$", value):
        raise ValidationError("Invalid phone number format.")
    return value

def validate_username(value):
    if not value or len(value) < 3:
        raise ValidationError("Username must be at least 3 characters long.")
    if not re.match(r"^[\w.@+-]+$", value):
        raise ValidationError("Username can only contain letters, numbers, and @/./+/-/_.")
    return value
