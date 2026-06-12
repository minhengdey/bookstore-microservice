from django import template
from datetime import datetime

register = template.Library()

# Bản đồ trạng thái đơn hàng → tiếng Việt
ORDER_STATUS_MAP = {
    # New statuses
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
    
    # Legacy statuses
    "PENDING_PAYMENT": "Chờ thanh toán",
    "PAID":            "Đã thanh toán",
    "PROCESSING":      "Đang xử lý",
    "SHIPPING":        "Đang giao",
    "DELIVERED":       "Đã giao",
    "CANCELLED":       "Đã hủy",
    "RETURN_REQUESTED":"Yêu cầu trả hàng",
    "RETURNED":        "Đã trả hàng",
    "REFUNDED":        "Đã hoàn tiền",
    "pending_payment": "Chờ thanh toán",
    "paid":            "Đã thanh toán",
    "pending":         "Chờ xử lý",
    "confirmed":       "Đã xác nhận",
    "processing":      "Đang xử lý",
    "shipped":         "Đang giao",
    "delivered":       "Đã giao",
    "cancelled":       "Đã hủy",
    "refunded":        "Đã hoàn tiền",
    "failed":          "Thất bại",
}


@register.filter
def vi_status(value):
    """Dịch trạng thái đơn hàng sang tiếng Việt."""
    if not value:
        return "—"
    return ORDER_STATUS_MAP.get(str(value), str(value).replace("_", " ").title())


@register.filter
def format_date(value):
    """
    Chuyển chuỗi ISO datetime (2026-05-31T07:28:06.992173) thành
    định dạng dễ đọc: 31/05/2026 07:28
    """
    if not value:
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    s = str(value).strip()
    # Thử parse ISO format theo thứ tự từ chi tiết nhất đến đơn giản nhất
    for fmt, length in (
        ("%Y-%m-%dT%H:%M:%S.%f", 26),
        ("%Y-%m-%dT%H:%M:%S",    19),
        ("%Y-%m-%d %H:%M:%S.%f", 26),
        ("%Y-%m-%d %H:%M:%S",    19),
        ("%Y-%m-%d",             10),
    ):
        try:
            dt = datetime.strptime(s[:length], fmt)
            return dt.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            continue
    return s


@register.filter
def vnd(value):
    """
    Format số thành tiền VND có dấu phân cách nghìn.
    Ví dụ: 1500000 → 1.500.000₫
    """
    try:
        amount = float(value)
        # Nếu là số nguyên, không hiển thị phần thập phân
        if amount == int(amount):
            formatted = f"{int(amount):,}".replace(",", ".")
        else:
            formatted = f"{amount:,.0f}".replace(",", ".")
        return f"{formatted}₫"
    except (TypeError, ValueError):
        return f"{value}₫" if value else "0₫"
