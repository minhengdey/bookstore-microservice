from rest_framework.exceptions import ValidationError

def validate_order_items(items):
    if not items or not isinstance(items, list):
        raise ValidationError("Order must contain at least one item.")
    for item in items:
        if "product_id" not in item or "quantity" not in item:
            raise ValidationError("Each item must have a product_id and quantity.")
        if int(item["quantity"]) <= 0:
            raise ValidationError("Item quantity must be greater than zero.")
    return items
