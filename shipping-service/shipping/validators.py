from rest_framework.exceptions import ValidationError

def validate_status(value):
    valid_statuses = ["pending", "processing", "shipped", "failed"]
    if value not in valid_statuses:
        raise ValidationError(f"Status must be one of {valid_statuses}")
    return value
