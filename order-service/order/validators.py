from rest_framework.exceptions import ValidationError

_SHIPPING_ADDRESS_FIELDS = {
    "recipient_name": "Tên người nhận",
    "phone": "Số điện thoại",
    "address_line": "Địa chỉ",
    "city": "Thành phố",
}


def validate_order_items(items):
    if not items or not isinstance(items, list):
        raise ValidationError("Đơn hàng phải có ít nhất một sản phẩm.")
    for item in items:
        if "product_id" not in item or "quantity" not in item:
            raise ValidationError("Mỗi sản phẩm phải có product_id và quantity.")
        if int(item["quantity"]) <= 0:
            raise ValidationError("Số lượng sản phẩm phải lớn hơn 0.")
        try:
            unit_price = float(item.get("unit_price", 0))
        except (TypeError, ValueError):
            unit_price = 0
        if unit_price <= 0:
            raise ValidationError("Giá sản phẩm không hợp lệ.")
    return items


def validate_shipping_address(shipping_address):
    if not shipping_address or not isinstance(shipping_address, dict):
        raise ValidationError("Vui lòng cung cấp địa chỉ giao hàng.")
    for field, label in _SHIPPING_ADDRESS_FIELDS.items():
        if not str(shipping_address.get(field) or "").strip():
            raise ValidationError(f"{label} là bắt buộc.")
    return shipping_address


def validate_create_order_payload(data: dict):
    validate_order_items(data.get("items", []))
    validate_shipping_address(data.get("shipping_address"))
    if not data.get("shipping_method_id"):
        raise ValidationError("Vui lòng chọn phương thức vận chuyển.")
    return data
