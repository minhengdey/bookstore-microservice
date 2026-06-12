from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import Voucher, FlashSaleItem


class VoucherError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def validate_voucher(code: str, order_amount) -> dict:
    if not code or not str(code).strip():
        raise VoucherError("Mã giảm giá không được để trống.")
    if order_amount is None:
        raise VoucherError("Thiếu giá trị đơn hàng.")

    try:
        voucher = Voucher.objects.get(code=str(code).strip().upper(), is_active=True)
    except Voucher.DoesNotExist:
        raise VoucherError("Mã giảm giá không hợp lệ.", status_code=404)

    now = timezone.now()
    if now < voucher.start_date:
        raise VoucherError("Mã giảm giá chưa có hiệu lực.")
    if now > voucher.end_date:
        raise VoucherError("Mã giảm giá đã hết hạn.")
    if voucher.used_count >= voucher.usage_limit:
        raise VoucherError("Mã giảm giá đã hết lượt sử dụng.")

    amount = Decimal(str(order_amount))
    if amount < voucher.min_order_value:
        raise VoucherError(
            f"Đơn hàng tối thiểu {int(voucher.min_order_value):,}₫ để dùng mã này."
        )

    discount = Decimal("0")
    if voucher.discount_percentage:
        discount = amount * voucher.discount_percentage / Decimal("100")
        if voucher.max_discount_amount and discount > voucher.max_discount_amount:
            discount = voucher.max_discount_amount
    elif voucher.discount_amount:
        discount = voucher.discount_amount

    if discount > amount:
        discount = amount

    return {
        "voucher_id": voucher.id,
        "code": voucher.code,
        "discount_amount": float(discount),
        "final_amount": float(amount - discount),
    }


@transaction.atomic
def consume_voucher(code: str, order_id=None) -> dict:
    voucher = (
        Voucher.objects.select_for_update()
        .filter(code=str(code).strip().upper(), is_active=True)
        .first()
    )
    if not voucher:
        raise VoucherError("Mã giảm giá không hợp lệ.", status_code=404)

    now = timezone.now()
    if now < voucher.start_date or now > voucher.end_date:
        raise VoucherError("Mã giảm giá không còn hiệu lực.")
    if voucher.used_count >= voucher.usage_limit:
        raise VoucherError("Mã giảm giá đã hết lượt sử dụng.")

    voucher.used_count += 1
    voucher.save(update_fields=["used_count"])
    return {"code": voucher.code, "used_count": voucher.used_count, "order_id": order_id}


def get_flash_sale_prices(product_ids: list[int]) -> dict:
    if not product_ids:
        return {}
    now = timezone.now()
    items = (
        FlashSaleItem.objects.filter(
            product_id__in=product_ids,
            flash_sale__is_active=True,
            flash_sale__start_date__lte=now,
            flash_sale__end_date__gte=now,
        )
        .select_related("flash_sale")
        .order_by("discount_price")
    )
    prices = {}
    for item in items:
        remaining = item.quantity - item.sold_count
        if remaining <= 0:
            continue
        pid = item.product_id
        price = float(item.discount_price)
        if pid not in prices or price < prices[pid]["price"]:
            prices[pid] = {
                "price": price,
                "flash_sale_id": item.flash_sale_id,
                "flash_sale_name": item.flash_sale.name,
                "remaining": remaining,
                "item_id": item.id,
            }
    return prices


@transaction.atomic
def consume_flash_sale_items(items: list[dict]) -> dict:
    consumed = []
    for entry in items:
        product_id = int(entry["product_id"])
        qty = int(entry.get("quantity", 1))
        flash_item = (
            FlashSaleItem.objects.select_for_update()
            .filter(
                product_id=product_id,
                flash_sale__is_active=True,
                flash_sale__start_date__lte=timezone.now(),
                flash_sale__end_date__gte=timezone.now(),
            )
            .order_by("discount_price")
            .first()
        )
        if not flash_item:
            continue
        remaining = flash_item.quantity - flash_item.sold_count
        if remaining < qty:
            raise VoucherError(f"Sản phẩm #{product_id} đã hết suất Flash Sale.")
        flash_item.sold_count += qty
        flash_item.save(update_fields=["sold_count"])
        consumed.append({"product_id": product_id, "quantity": qty, "item_id": flash_item.id})
    return {"consumed": consumed}
