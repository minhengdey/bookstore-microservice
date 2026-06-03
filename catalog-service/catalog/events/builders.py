class EventBuilder:
    @staticmethod
    def build_product_created(product):
        return {
            "product_id": str(product.id),
            "name": product.name,
            "brand_id": str(product.brand_id) if product.brand_id else None,
            "category_id": str(product.category_id) if product.category_id else None,
            "created_at": product.created_at.isoformat()
        }

    @staticmethod
    def build_product_updated(product):
        return {
            "product_id": str(product.id),
            "name": product.name,
            "brand_id": str(product.brand_id) if product.brand_id else None,
            "category_id": str(product.category_id) if product.category_id else None,
            "is_active": product.is_active,
            "updated_at": product.updated_at.isoformat()
        }

    @staticmethod
    def build_product_deleted(product):
        return {
            "product_id": str(product.id),
            "deleted_at": product.deleted_at.isoformat() if product.deleted_at else None
        }

    @staticmethod
    def build_variant_created(variant):
        return {
            "variant_id": str(variant.id),
            "product_id": str(variant.product_id),
            "sku": variant.sku,
            "price": str(variant.price),
            "created_at": variant.created_at.isoformat()
        }

    @staticmethod
    def build_variant_updated(variant):
        return {
            "variant_id": str(variant.id),
            "product_id": str(variant.product_id),
            "sku": variant.sku,
            "price": str(variant.price),
            "is_active": variant.is_active,
            "updated_at": variant.updated_at.isoformat()
        }

    @staticmethod
    def build_variant_deleted(variant):
        return {
            "variant_id": str(variant.id),
            "product_id": str(variant.product_id),
            "deleted_at": variant.deleted_at.isoformat() if variant.deleted_at else None
        }

    @staticmethod
    def build_category_created(category):
        return {
            "category_id": str(category.id),
            "name": category.name,
            "slug": category.slug,
            "full_path": category.full_path,
            "level": category.level,
            "created_at": category.created_at.isoformat()
        }

    @staticmethod
    def build_category_updated(category):
        return {
            "category_id": str(category.id),
            "name": category.name,
            "slug": category.slug,
            "full_path": category.full_path,
            "level": category.level,
            "updated_at": category.updated_at.isoformat()
        }
