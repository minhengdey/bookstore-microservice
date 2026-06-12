import logging
from datetime import date, timedelta

from django.db import IntegrityError, transaction

from .models import Shipping, ShippingAddress, ShippingMethod, ShippingState, ShippingStatus, ShippingZone

logger = logging.getLogger(__name__)


class ShippingMethodService:
    def list(self):
        return ShippingMethod.objects.all()

    def get(self, pk):
        m = ShippingMethod.objects.filter(pk=pk).first()
        if not m:
            raise ValueError(f"ShippingMethod {pk} not found")
        return m

    def create(self, data):
        return ShippingMethod.objects.create(**data)

    def calculate_fee(self, method_id, total_weight=1.0, distance_km=10.0):
        """Tính phí ship động: phí cơ bản + phụ phí theo khối lượng và khoảng cách."""
        method = self.get(method_id)
        base = float(method.rate)
        weight = max(0.0, float(total_weight) - float(method.min_weight or 0))
        distance = max(0.0, float(distance_km) - float(method.min_distance or 0))
        weight_fee = weight * 5000
        distance_fee = distance * 1000
        total_fee = round(base + weight_fee + distance_fee)
        return {
            "shipping_method_id": method.id,
            "method_name": method.method_name,
            "base_rate": base,
            "weight_fee": weight_fee,
            "distance_fee": distance_fee,
            "shipping_fee": total_fee,
            "total_weight": total_weight,
            "distance_km": distance_km,
        }


class ShippingZoneService:
    DEFAULT_DISTANCE_KM = 15.0

    def lookup_distance(self, city):
        if not city:
            return self.DEFAULT_DISTANCE_KM
        normalized = str(city).strip()
        zone = ShippingZone.objects.filter(city_name__iexact=normalized).first()
        if zone:
            return float(zone.distance_km)
        return self.DEFAULT_DISTANCE_KM


class InvalidShippingTransition(Exception):
    pass


class ShippingService:
    def list(self):
        return Shipping.objects.prefetch_related("address", "statuses", "shipping_method").all()

    def get(self, pk):
        s = Shipping.objects.prefetch_related("address", "statuses", "shipping_method").filter(pk=pk).first()
        if not s:
            raise ValueError(f"Shipping {pk} not found")
        return s

    def get_by_order_id(self, order_id):
        return Shipping.objects.prefetch_related("address", "statuses", "shipping_method").filter(order_id=order_id).first()

    def _assign_tracking_number(self, shipping):
        if not shipping.tracking_number:
            shipping.tracking_number = f"SHIP-{shipping.id:08d}"
            shipping.save(update_fields=["tracking_number"])

    def _create_address(self, shipping, address_data):
        if not address_data or ShippingAddress.objects.filter(shipping=shipping).exists():
            return
        ShippingAddress.objects.create(
            shipping=shipping,
            recipient_name=address_data.get("recipient_name", ""),
            address_line=address_data.get("address_line", ""),
            city=address_data.get("city", ""),
            state=address_data.get("state", ""),
            country=address_data.get("country", "Việt Nam"),
            postal_code=address_data.get("postal_code", ""),
            phone=address_data.get("phone", ""),
        )

    def _estimated_delivery_date(self, method):
        if not method:
            return None
        days = method.estimated_days or 5
        return date.today() + timedelta(days=days)

    def create_shipping(self, order_id: int, *, shipping_method_id=None, address_data=None):
        """
        Idempotent shipping creation with full address/method/tracking data in DB.
        """
        with transaction.atomic():
            shipping = Shipping.objects.filter(order_id=order_id).first()
            if shipping:
                if shipping_method_id and not shipping.shipping_method_id:
                    method = ShippingMethod.objects.filter(pk=shipping_method_id).first()
                    if method:
                        shipping.shipping_method = method
                        if not shipping.estimated_delivery_date:
                            shipping.estimated_delivery_date = self._estimated_delivery_date(method)
                        shipping.save(update_fields=["shipping_method", "estimated_delivery_date"])
                if address_data and not ShippingAddress.objects.filter(shipping=shipping).exists():
                    self._create_address(shipping, address_data)
                self._assign_tracking_number(shipping)
                return shipping

            method = None
            estimated_delivery_date = None
            if shipping_method_id:
                method = ShippingMethod.objects.filter(pk=shipping_method_id).first()
                if method:
                    estimated_delivery_date = self._estimated_delivery_date(method)

            try:
                shipping = Shipping.objects.create(
                    order_id=order_id,
                    status=ShippingState.PENDING,
                    shipping_method=method,
                    estimated_delivery_date=estimated_delivery_date,
                )
            except IntegrityError:
                shipping = Shipping.objects.get(order_id=order_id)
                return shipping

            self._assign_tracking_number(shipping)
            self._create_address(shipping, address_data)
            ShippingStatus.objects.create(
                shipping=shipping,
                status=ShippingState.PENDING,
                description="Đã nhận yêu cầu giao hàng.",
            )

        return shipping

    def update_shipping_status(
        self,
        shipping_id: int,
        new_status: str,
        description: str = "",
        timeline_status: str | None = None,
    ):
        """
        State Machine Enforcement:
        PENDING -> PROCESSING
        PROCESSING -> SHIPPED | FAILED
        FAILED -> PROCESSING (retry)
        """
        with transaction.atomic():
            shipping = self.get(shipping_id)
            current_status = shipping.status

            allowed = False
            if current_status == ShippingState.PENDING and new_status == ShippingState.PROCESSING:
                allowed = True
            elif current_status == ShippingState.PROCESSING and new_status in (ShippingState.SHIPPED, ShippingState.FAILED):
                allowed = True
            elif current_status == ShippingState.FAILED and new_status == ShippingState.PROCESSING:
                allowed = True

            if not allowed:
                raise InvalidShippingTransition(f"Invalid transition from {current_status} to {new_status}")

            shipping.status = new_status
            shipping.save(update_fields=["status"])

            ShippingStatus.objects.create(
                shipping=shipping,
                status=timeline_status or new_status,
                description=description,
            )

        return shipping

    def sync_from_order_status(self, shipping_id: int, raw_status: str):
        """Đồng bộ từ order-service với mô tả tiếng Việt cho khách hàng."""
        sync_map = {
            "in_transit": {
                "state": ShippingState.PROCESSING,
                "timeline": "in_transit",
                "description": "Đơn hàng đang được vận chuyển.",
            },
            "delivered": {
                "state": ShippingState.SHIPPED,
                "timeline": "delivered",
                "description": "Đơn hàng đã giao thành công.",
            },
            "processing": {
                "state": ShippingState.PROCESSING,
                "timeline": "processing",
                "description": "Đơn hàng đang được chuẩn bị giao.",
            },
            "shipped": {
                "state": ShippingState.SHIPPED,
                "timeline": "delivered",
                "description": "Đơn hàng đã giao thành công.",
            },
        }
        meta = sync_map.get(str(raw_status).lower(), sync_map["processing"])

        with transaction.atomic():
            shipping = self.get(shipping_id)
            target_state = meta["state"]
            timeline_status = meta["timeline"]
            description = meta["description"]

            if shipping.status != target_state:
                try:
                    self.update_shipping_status(
                        shipping_id,
                        target_state,
                        description,
                        timeline_status=timeline_status,
                    )
                except InvalidShippingTransition:
                    shipping.status = target_state
                    shipping.save(update_fields=["status"])
                    ShippingStatus.objects.create(
                        shipping=shipping,
                        status=timeline_status,
                        description=description,
                    )
            else:
                latest = shipping.statuses.order_by("-updated_date").first()
                if not latest or latest.status != timeline_status:
                    ShippingStatus.objects.create(
                        shipping=shipping,
                        status=timeline_status,
                        description=description,
                    )

        return self.get(shipping_id)
