from django.db import transaction
from django.db.models import Min, Max
from catalog.models import Product, ProductVariant, OutboxEvent, AuditLog
from catalog.events import PRODUCT_CREATED, PRODUCT_UPDATED, PRODUCT_DELETED, VARIANT_CREATED, VARIANT_UPDATED, VARIANT_DELETED
from catalog.events.builders import EventBuilder
import uuid

class ProductService:
    @staticmethod
    @transaction.atomic
    def create_product(data, user_id=None, trace_context=None):
        product = Product.objects.create(**data)
        
        event_payload = EventBuilder.build_product_created(product)
        
        OutboxEvent.objects.create(
            aggregate_id=product.id,
            aggregate_type='Product',
            event_type=PRODUCT_CREATED,
            message_id=uuid.uuid4(),
            payload=event_payload,
            status='PENDING'
        )
        
        trace_kwargs = ProductService._extract_trace(trace_context)
        AuditLog.objects.create(
            aggregate_id=product.id,
            aggregate_type='Product',
            action='CREATE',
            actor_id=user_id,
            actor_type='ADMIN',  # Defaulting, can be dynamic based on request
            payload_after=event_payload,
            **trace_kwargs
        )
        return product
        
    @staticmethod
    @transaction.atomic
    def update_product(product, data, user_id=None, trace_context=None):
        payload_before = EventBuilder.build_product_updated(product)
        
        for key, value in data.items():
            setattr(product, key, value)
        product.save()
        
        payload_after = EventBuilder.build_product_updated(product)
        
        OutboxEvent.objects.create(
            aggregate_id=product.id,
            aggregate_type='Product',
            event_type=PRODUCT_UPDATED,
            message_id=uuid.uuid4(),
            payload=payload_after,
            status='PENDING'
        )
        
        trace_kwargs = ProductService._extract_trace(trace_context)
        AuditLog.objects.create(
            aggregate_id=product.id,
            aggregate_type='Product',
            action='UPDATE',
            actor_id=user_id,
            actor_type='ADMIN',
            payload_before=payload_before,
            payload_after=payload_after,
            **trace_kwargs
        )
        return product

    @staticmethod
    @transaction.atomic
    def delete_product(product, user_id=None, trace_context=None):
        payload_before = EventBuilder.build_product_deleted(product)
        
        product.delete() # triggers soft delete if using SoftDeleteModel overrides, else we just set deleted_at
        # Assuming product.delete() sets deleted_at and saves.
        
        payload_after = EventBuilder.build_product_deleted(product)
        
        OutboxEvent.objects.create(
            aggregate_id=product.id,
            aggregate_type='Product',
            event_type=PRODUCT_DELETED,
            message_id=uuid.uuid4(),
            payload=payload_after,
            status='PENDING'
        )
        
        trace_kwargs = ProductService._extract_trace(trace_context)
        AuditLog.objects.create(
            aggregate_id=product.id,
            aggregate_type='Product',
            action='DELETE',
            actor_id=user_id,
            actor_type='ADMIN',
            payload_before=payload_before,
            payload_after=payload_after,
            **trace_kwargs
        )
        
    @staticmethod
    def recalculate_price_range(product_id):
        # We need to compute min and max price from active variants
        result = ProductVariant.objects.filter(
            product_id=product_id, is_active=True
        ).aggregate(
            min_price=Min('price'),
            max_price=Max('price')
        )
        
        Product.objects.filter(id=product_id).update(
            min_price=result['min_price'],
            max_price=result['max_price']
        )

    @staticmethod
    @transaction.atomic
    def create_variant(data, user_id=None, trace_context=None):
        variant = ProductVariant.objects.create(**data)
        ProductService.recalculate_price_range(variant.product_id)
        
        event_payload = EventBuilder.build_variant_created(variant)
        
        OutboxEvent.objects.create(
            aggregate_id=variant.id,
            aggregate_type='ProductVariant',
            event_type=VARIANT_CREATED,
            message_id=uuid.uuid4(),
            payload=event_payload,
            status='PENDING'
        )
        
        trace_kwargs = ProductService._extract_trace(trace_context)
        AuditLog.objects.create(
            aggregate_id=variant.id,
            aggregate_type='ProductVariant',
            action='CREATE',
            actor_id=user_id,
            actor_type='ADMIN',
            payload_after=event_payload,
            **trace_kwargs
        )
        return variant

    @staticmethod
    @transaction.atomic
    def update_variant(variant, data, user_id=None, trace_context=None):
        payload_before = EventBuilder.build_variant_updated(variant)
        
        for key, value in data.items():
            setattr(variant, key, value)
        variant.save()
        
        # Recalculate price in case price or is_active changed
        ProductService.recalculate_price_range(variant.product_id)
        
        payload_after = EventBuilder.build_variant_updated(variant)
        
        OutboxEvent.objects.create(
            aggregate_id=variant.id,
            aggregate_type='ProductVariant',
            event_type=VARIANT_UPDATED,
            message_id=uuid.uuid4(),
            payload=payload_after,
            status='PENDING'
        )
        
        trace_kwargs = ProductService._extract_trace(trace_context)
        AuditLog.objects.create(
            aggregate_id=variant.id,
            aggregate_type='ProductVariant',
            action='UPDATE',
            actor_id=user_id,
            actor_type='ADMIN',
            payload_before=payload_before,
            payload_after=payload_after,
            **trace_kwargs
        )
        return variant

    @staticmethod
    @transaction.atomic
    def delete_variant(variant, user_id=None, trace_context=None):
        payload_before = EventBuilder.build_variant_deleted(variant)
        
        product_id = variant.product_id
        variant.delete()
        ProductService.recalculate_price_range(product_id)
        
        payload_after = EventBuilder.build_variant_deleted(variant)
        
        OutboxEvent.objects.create(
            aggregate_id=variant.id,
            aggregate_type='ProductVariant',
            event_type=VARIANT_DELETED,
            message_id=uuid.uuid4(),
            payload=payload_after,
            status='PENDING'
        )
        
        trace_kwargs = ProductService._extract_trace(trace_context)
        AuditLog.objects.create(
            aggregate_id=variant.id,
            aggregate_type='ProductVariant',
            action='DELETE',
            actor_id=user_id,
            actor_type='ADMIN',
            payload_before=payload_before,
            payload_after=payload_after,
            **trace_kwargs
        )

    @staticmethod
    def _extract_trace(trace_context):
        if not trace_context:
            return {}
        return {
            'trace_id': trace_context.get('trace_id'),
            'span_id': trace_context.get('span_id'),
            'correlation_id': trace_context.get('correlation_id'),
            'request_id': trace_context.get('request_id'),
        }
