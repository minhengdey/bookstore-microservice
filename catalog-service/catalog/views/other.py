from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from catalog.models import Brand, Category, ProductVariant, ProductImage, Review
from catalog.serializers import BrandSerializer, CategorySerializer, ProductVariantSerializer, ProductImageSerializer, ReviewSerializer
from catalog.permissions import IsCatalogAdmin
from catalog.services.category_service import CategoryService
from catalog.services.product_service import ProductService

class BaseCatalogViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [IsCatalogAdmin]
        return [permission() for permission in permission_classes]

class BrandViewSet(BaseCatalogViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

class CategoryViewSet(BaseCatalogViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'slug']

    def perform_create(self, serializer):
        CategoryService.create_category(
            name=serializer.validated_data['name'],
            parent_id=serializer.validated_data.get('parent').id if serializer.validated_data.get('parent') else None
        )

    def perform_update(self, serializer):
        CategoryService.update_category(
            self.get_object(),
            name=serializer.validated_data.get('name'),
            parent_id=serializer.validated_data.get('parent').id if serializer.validated_data.get('parent') else None
        )

class ProductVariantViewSet(BaseCatalogViewSet):
    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantSerializer

    def perform_create(self, serializer):
        user_id = self.request.META.get('HTTP_X_USER_ID')
        variant = ProductService.create_variant(serializer.validated_data, user_id=user_id)
        serializer.instance = variant

    def perform_update(self, serializer):
        user_id = self.request.META.get('HTTP_X_USER_ID')
        variant = ProductService.update_variant(self.get_object(), serializer.validated_data, user_id=user_id)
        serializer.instance = variant

    def perform_destroy(self, instance):
        user_id = self.request.META.get('HTTP_X_USER_ID')
        ProductService.delete_variant(instance, user_id=user_id)

class ProductImageViewSet(BaseCatalogViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer

class ReviewViewSet(BaseCatalogViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product', 'rating']
    ordering_fields = ['created_at']
