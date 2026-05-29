from rest_framework.exceptions import ValidationError

def validate_quantity(value):
    if value is not None and int(value) <= 0:
        raise ValidationError("Quantity must be greater than zero.")
    return value
