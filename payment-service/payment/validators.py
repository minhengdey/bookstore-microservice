from rest_framework.exceptions import ValidationError

def validate_amount(value):
    if value is None or float(value) <= 0:
        raise ValidationError("Amount must be greater than zero.")
    return value
