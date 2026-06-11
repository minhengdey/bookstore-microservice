import logging
from django.db import transaction
from .models import Shipping, ShippingMethod, ShippingStatus, ShippingState

logger = logging.getLogger(__name__)

class ShippingMethodService:
    def list(self): return ShippingMethod.objects.all()
    def get(self, pk):
        m = ShippingMethod.objects.filter(pk=pk).first()
        if not m: raise ValueError(f"ShippingMethod {pk} not found")
        return m
    def create(self, data): return ShippingMethod.objects.create(**data)

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

from django.db import IntegrityError

class InvalidShippingTransition(Exception):
    pass

class ShippingService:
    def list(self): return Shipping.objects.prefetch_related('address', 'statuses').all()
    def get(self, pk):
        s = Shipping.objects.prefetch_related('address', 'statuses').filter(pk=pk).first()
        if not s: raise ValueError(f"Shipping {pk} not found")
        return s

    def create_shipping(self, order_id: int):
        """
        Pure idempotent function. Used internally via HTTP or future async consumer.
        """
        with transaction.atomic():
            try:
                shipping, created = Shipping.objects.get_or_create(
                    order_id=order_id,
                    defaults={
                        "status": ShippingState.PENDING,
                    }
                )
            except IntegrityError:
                shipping = Shipping.objects.get(order_id=order_id)
                created = False
            
            if not created:
                # Already exists, idempotent return
                return shipping
                
            # Log initial status
            ShippingStatus.objects.create(
                shipping=shipping,
                status=ShippingState.PENDING,
                description="Shipping request received."
            )
            
        return shipping

    def update_shipping_status(self, shipping_id: int, new_status: str, description: str = ""):
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
                status=new_status,
                description=description
            )
            
        return shipping
