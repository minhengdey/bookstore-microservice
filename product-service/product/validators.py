from rest_framework.exceptions import ValidationError

def validate_price(value):
    if value is not None and float(value) < 0:
        raise ValidationError("Price cannot be negative.")
    return value

def validate_stock(value):
    if value is not None and int(value) < 0:
        raise ValidationError("Stock cannot be negative.")
    return value
