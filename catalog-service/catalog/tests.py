from django.test import TestCase
from django.db import IntegrityError, transaction
# pyrefly: ignore [missing-import]
from rest_framework.exceptions import ValidationError
from catalog.models import Product, ProductVariant, Brand, Category, ProductImage
from catalog.services.product_service import ProductService
from catalog.services.category_service import CategoryService

class CatalogServiceTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name="Test Brand")
        self.category = CategoryService.create_category(name="Test Category")

    def test_soft_delete_variant_recalculates_price(self):
        product = ProductService.create_product({
            'name': 'Test Product',
            'brand_id': self.brand.id,
            'category_id': self.category.id
        })

        variant_a = ProductService.create_variant({
            'product_id': product.id,
            'sku': 'SKU-A',
            'price': 100
        })
        
        variant_b = ProductService.create_variant({
            'product_id': product.id,
            'sku': 'SKU-B',
            'price': 200
        })

        product.refresh_from_db()
        self.assertEqual(product.min_price, 100)
        self.assertEqual(product.max_price, 200)

        # Soft delete variant_a
        ProductService.delete_variant(variant_a)

        product.refresh_from_db()
        # The price should recalculate based only on active variant_b
        self.assertEqual(product.min_price, 200)
        self.assertEqual(product.max_price, 200)

    def test_category_cycle_prevention(self):
        electronics = CategoryService.create_category(name="Electronics")
        mobile = CategoryService.create_category(name="Mobile", parent_id=electronics.id)
        android = CategoryService.create_category(name="Android", parent_id=mobile.id)

        # Attempt to set Android as parent of Electronics
        with self.assertRaises(ValidationError) as context:
            CategoryService.update_category(electronics, parent_id=android.id)
        
        self.assertIn("Cycle detected", str(context.exception))

    def test_unique_primary_image_constraint_product(self):
        product = ProductService.create_product({
            'name': 'Image Test',
            'brand_id': self.brand.id,
            'category_id': self.category.id
        })

        # First primary image should succeed
        ProductImage.objects.create(product=product, image_key='img1.jpg', is_primary=True)

        # Second primary image should raise IntegrityError
        with self.assertRaises(IntegrityError):
            ProductImage.objects.create(product=product, image_key='img2.jpg', is_primary=True)

    def test_unique_primary_image_constraint_variant(self):
        product = ProductService.create_product({
            'name': 'Var Image Test',
            'brand_id': self.brand.id,
            'category_id': self.category.id
        })
        variant = ProductService.create_variant({
            'product_id': product.id,
            'sku': 'SKU-IMG',
            'price': 100
        })

        # First primary image should succeed
        ProductImage.objects.create(variant=variant, image_key='vimg1.jpg', is_primary=True)

        # Second primary image should raise IntegrityError
        with self.assertRaises(IntegrityError):
            ProductImage.objects.create(variant=variant, image_key='vimg2.jpg', is_primary=True)

    def test_image_xor_constraint(self):
        from django.db import transaction
        product = ProductService.create_product({
            'name': 'XOR Test',
            'brand_id': self.brand.id,
            'category_id': self.category.id
        })
        variant = ProductService.create_variant({
            'product_id': product.id,
            'sku': 'SKU-XOR',
            'price': 100
        })

        # Try to attach to both
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                ProductImage.objects.create(product=product, variant=variant, image_key='fail.jpg')

        # Try to attach to neither
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                ProductImage.objects.create(image_key='fail2.jpg')
