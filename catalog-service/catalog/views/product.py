from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from catalog.models import Product
from catalog.serializers.product import ProductListSerializer, ProductDetailSerializer
from catalog.permissions import IsCatalogAdmin
from catalog.services.product_service import ProductService

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('brand', 'category').prefetch_related('images', 'variants')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['brand', 'category', 'is_active', 'min_price', 'max_price']
    search_fields = ['name', 'description']
    ordering_fields = ['min_price', 'max_price', 'created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        return ProductDetailSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [IsCatalogAdmin]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        # Delegate to service for transactional outbox
        # We pass validated_data to service instead of standard serializer.save()
        user_id = self.request.META.get('HTTP_X_USER_ID')
        # Here we extract open telemetry context if provided in headers
        trace_context = {
            'trace_id': self.request.META.get('HTTP_TRACEPARENT', '').split('-')[1] if self.request.META.get('HTTP_TRACEPARENT') else None,
            'span_id': self.request.META.get('HTTP_TRACEPARENT', '').split('-')[2] if self.request.META.get('HTTP_TRACEPARENT') else None,
            'correlation_id': self.request.META.get('HTTP_X_CORRELATION_ID'),
            'request_id': self.request.META.get('HTTP_X_REQUEST_ID'),
        }
        product = ProductService.create_product(serializer.validated_data, user_id=user_id, trace_context=trace_context)
        # To make DRF happy with the returned instance
        serializer.instance = product

    def perform_update(self, serializer):
        user_id = self.request.META.get('HTTP_X_USER_ID')
        trace_context = {
            'trace_id': self.request.META.get('HTTP_TRACEPARENT', '').split('-')[1] if self.request.META.get('HTTP_TRACEPARENT') else None,
            'span_id': self.request.META.get('HTTP_TRACEPARENT', '').split('-')[2] if self.request.META.get('HTTP_TRACEPARENT') else None,
            'correlation_id': self.request.META.get('HTTP_X_CORRELATION_ID'),
            'request_id': self.request.META.get('HTTP_X_REQUEST_ID'),
        }
        product = ProductService.update_product(self.get_object(), serializer.validated_data, user_id=user_id, trace_context=trace_context)
        serializer.instance = product

    def perform_destroy(self, instance):
        user_id = self.request.META.get('HTTP_X_USER_ID')
        trace_context = {
            'trace_id': self.request.META.get('HTTP_TRACEPARENT', '').split('-')[1] if self.request.META.get('HTTP_TRACEPARENT') else None,
            'span_id': self.request.META.get('HTTP_TRACEPARENT', '').split('-')[2] if self.request.META.get('HTTP_TRACEPARENT') else None,
            'correlation_id': self.request.META.get('HTTP_X_CORRELATION_ID'),
            'request_id': self.request.META.get('HTTP_X_REQUEST_ID'),
        }
        ProductService.delete_product(instance, user_id=user_id, trace_context=trace_context)
