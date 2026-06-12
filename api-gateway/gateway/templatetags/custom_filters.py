from django import template
from django.utils.safestring import mark_safe
from datetime import datetime

register = template.Library()

ORDER_STATUS_MAP = {
    "DRAFT": "Bản nháp",
    "RESERVING_STOCK": "Đang giữ hàng",
    "STOCK_RESERVED": "Đã giữ hàng",
    "PAYMENT_PENDING": "Chờ thanh toán",
    "PAYMENT_PROCESSING": "Đang thanh toán",
    "WAITING_INVENTORY_CONFIRM": "Đã thanh toán",
    "COMPLETED": "Hoàn tất",
    "PAYMENT_FAILED": "Thanh toán thất bại",
    "CANCELLING": "Đang hủy",
    "CANCELLED": "Đã hủy",
    "REFUND_PENDING": "Chờ hoàn tiền",
    "REFUNDED": "Đã hoàn tiền",
    "PENDING_PAYMENT": "Chờ thanh toán",
    "PAID": "Đã thanh toán",
    "PROCESSING": "Đang xử lý",
    "SHIPPING": "Đang giao",
    "DELIVERED": "Đã giao",
    "RETURN_REQUESTED": "Yêu cầu trả hàng",
    "RETURNED": "Đã trả hàng",
    "pending_payment": "Chờ thanh toán",
    "paid": "Đã thanh toán",
    "pending": "Chờ xử lý",
    "confirmed": "Đã xác nhận",
    "processing": "Đang xử lý",
    "shipped": "Đang giao",
    "delivered": "Đã giao",
    "cancelled": "Đã hủy",
    "refunded": "Đã hoàn tiền",
    "failed": "Thất bại",
    "failed_payment": "Thanh toán thất bại",
}

SHIPPING_STATUS_MAP = {
    "pending": "Chờ xử lý",
    "PENDING": "Chờ xử lý",
    "processing": "Đang vận chuyển",
    "PROCESSING": "Đang vận chuyển",
    "shipped": "Đã giao hàng",
    "SHIPPED": "Đã giao hàng",
    "in_transit": "Đang vận chuyển",
    "IN_TRANSIT": "Đang vận chuyển",
    "out_for_delivery": "Đang giao đến bạn",
    "OUT_FOR_DELIVERY": "Đang giao đến bạn",
    "delivered": "Đã giao hàng",
    "DELIVERED": "Đã giao hàng",
    "failed": "Giao hàng thất bại",
    "FAILED": "Giao hàng thất bại",
    "returned": "Hoàn trả",
    "RETURNED": "Hoàn trả",
}

TICKET_STATUS_MAP = {
    "OPEN": "Chờ xử lý",
    "IN_PROGRESS": "Đang xử lý",
    "RESOLVED": "Đã giải quyết",
    "CLOSED": "Đã đóng",
}

CUSTOMER_STATUS_MAP = {
    "ACTIVE": "Hoạt động",
    "INACTIVE": "Ngừng hoạt động",
    "SUSPENDED": "Tạm khóa",
    "BANNED": "Đã cấm",
}

PRODUCT_ATTR_LABELS = {
    "color": "Màu sắc",
    "size": "Kích cỡ",
    "weight": "Trọng lượng",
    "brand": "Thương hiệu",
    "material": "Chất liệu",
    "warranty": "Bảo hành",
    "dimensions": "Kích thước",
    "capacity": "Dung tích",
    "origin": "Xuất xứ",
    "model": "Model",
    "storage": "Bộ nhớ",
    "ram": "RAM",
    "screen": "Màn hình",
    "battery": "Pin",
    "cpu": "Bộ xử lý",
    "features": "Tính năng",
    "suction": "Lực hút",
    "switch": "Switch",
    "layout": "Bố cục",
    "connectivity": "Kết nối",
    "size": "Kích cỡ",
    "resolution": "Độ phân giải",
    "refresh_rate": "Tần số quét",
    "power": "Công suất",
    "jar": "Dung tích cốc",
    "volume": "Dung tích",
    "skin_type": "Loại da",
    "shade": "Màu",
    "thickness": "Độ dày",
    "size_range": "Size",
    "gender": "Giới tính",
    "fit": "Form dáng",
    "style": "Kiểu dáng",
}


def _normalize_status(value):
    if value is None:
        return ""
    return str(value).strip()


@register.filter
def vi_status(value):
    """Dịch trạng thái đơn hàng sang tiếng Việt."""
    if not value:
        return "—"
    key = _normalize_status(value)
    return ORDER_STATUS_MAP.get(key, ORDER_STATUS_MAP.get(key.upper(), key.replace("_", " ").title()))


@register.filter
def customer_display(value):
    """Hiển thị tên khách: ưu tiên full_name/username đã enrich, không dùng 'Khách #id'."""
    text = (value or "").strip()
    return text if text else "Khách hàng"


@register.filter
def vi_shipping_status(value):
    """Dịch trạng thái vận chuyển sang tiếng Việt."""
    if not value:
        return "—"
    key = _normalize_status(value)
    return SHIPPING_STATUS_MAP.get(key, SHIPPING_STATUS_MAP.get(key.lower(), key.replace("_", " ").title()))


_SYNC_DESCRIPTION_MAP = {
    "in_transit": "Đơn hàng đang được vận chuyển.",
    "delivered": "Đơn hàng đã giao thành công.",
    "processing": "Đơn hàng đang được chuẩn bị giao.",
    "shipped": "Đơn hàng đã giao thành công.",
    "pending": "Đã nhận yêu cầu giao hàng.",
}


@register.filter
def shipping_timeline_description(value):
    """Chuyển mô tả timeline shipping sang tiếng Việt (kể cả bản ghi sync cũ)."""
    if not value:
        return ""
    text = str(value).strip()
    lowered = text.lower()
    if lowered.startswith("synced from order-service:") or lowered.startswith("synced:"):
        raw = text.split(":", 1)[-1].strip().lower()
        return _SYNC_DESCRIPTION_MAP.get(raw, "Cập nhật trạng thái giao hàng.")
    return text


@register.filter
def vi_ticket_status(value):
    """Dịch trạng thái ticket hỗ trợ sang tiếng Việt."""
    if not value:
        return "—"
    key = _normalize_status(value).upper()
    return TICKET_STATUS_MAP.get(key, key.replace("_", " ").lower())


@register.filter
def vi_customer_status(value):
    """Dịch trạng thái khách hàng sang tiếng Việt."""
    if not value:
        return "—"
    return CUSTOMER_STATUS_MAP.get(_normalize_status(value).upper(), str(value).replace("_", " ").title())


@register.filter
def attr_label(value):
    """Dịch tên thuộc tính sản phẩm sang tiếng Việt."""
    if not value:
        return ""
    key = str(value).strip().lower()
    return PRODUCT_ATTR_LABELS.get(key, str(value).replace("_", " ").title())


@register.filter
def attr_value(value):
    """Hiển thị giá trị thuộc tính (list/dict/scalar)."""
    if value is None:
        return "—"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return "; ".join(f"{k}: {v}" for k, v in value.items())
    return value


@register.filter
def order_status_badge(value):
    """Trả về class badge CSS cho trạng thái đơn hàng."""
    key = _normalize_status(value).upper()
    success = {"DELIVERED", "COMPLETED", "REFUNDED"}
    info = {"PAID", "PROCESSING", "SHIPPING", "WAITING_INVENTORY_CONFIRM", "CONFIRMED"}
    danger = {"CANCELLED", "FAILED", "FAILED_PAYMENT", "PAYMENT_FAILED", "RETURNED"}
    warning = {"PENDING_PAYMENT", "PAYMENT_PENDING", "RETURN_REQUESTED", "REFUND_PENDING", "PENDING", "DRAFT"}
    if key in success or _normalize_status(value).lower() in {"delivered", "completed", "refunded"}:
        return "badge-success"
    if key in info or _normalize_status(value).lower() in {"paid", "processing", "shipped", "confirmed"}:
        return "badge-info"
    if key in danger or _normalize_status(value).lower() in {"cancelled", "failed", "failed_payment"}:
        return "badge-danger"
    if key in warning:
        return "badge-warning"
    return "badge-secondary"


@register.filter
def ticket_status_badge(value):
    """Trả về class badge CSS cho trạng thái ticket."""
    key = _normalize_status(value).upper()
    mapping = {
        "OPEN": "badge-danger",
        "IN_PROGRESS": "badge-info",
        "RESOLVED": "badge-success",
        "CLOSED": "badge-secondary",
    }
    return mapping.get(key, "badge-secondary")


@register.filter
def format_date(value):
    """Chuyển chuỗi ISO datetime thành định dạng dễ đọc."""
    if not value:
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    s = str(value).strip()
    for fmt, length in (
        ("%Y-%m-%dT%H:%M:%S.%f", 26),
        ("%Y-%m-%dT%H:%M:%S", 19),
        ("%Y-%m-%d %H:%M:%S.%f", 26),
        ("%Y-%m-%d %H:%M:%S", 19),
        ("%Y-%m-%d", 10),
    ):
        try:
            dt = datetime.strptime(s[:length], fmt)
            return dt.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            continue
    return s


@register.filter
def star_rating(value):
    """Hiển thị rating dạng sao (1–5)."""
    try:
        n = max(0, min(5, round(float(value))))
    except (TypeError, ValueError):
        n = 0
    filled = "★" * n
    empty = "☆" * (5 - n)
    return mark_safe(
        f'<span class="star-rating-display" aria-label="{n} trên 5 sao">'
        f'<span class="star-rating-filled">{filled}</span>'
        f'<span class="star-rating-empty">{empty}</span></span>'
    )


@register.filter
def vnd(value):
    """Format số thành tiền VND có dấu phân cách nghìn."""
    try:
        amount = float(value)
        if amount == int(amount):
            formatted = f"{int(amount):,}".replace(",", ".")
        else:
            formatted = f"{amount:,.0f}".replace(",", ".")
        return f"{formatted}₫"
    except (TypeError, ValueError):
        return f"{value}₫" if value else "0₫"
