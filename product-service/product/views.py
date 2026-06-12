import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from common.auth import require_auth, require_staff, require_internal
from .services import ProductService, CategoryService, BrandService, ProductVariantService, redis_client
from .serializers import ProductSerializer, CategorySerializer, BrandSerializer, ProductVariantSerializer, InventoryTransactionSerializer
from .models import InventoryTransaction

_prod_svc = ProductService()
_cat_svc = CategoryService()
_brand_svc = BrandService()
_var_svc = ProductVariantService()

def _parse_positive_int(value, default):
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default

class ProductListView(APIView):
    def get(self, request):
        page = _parse_positive_int(request.query_params.get("page"), 1)
        page_size = min(_parse_positive_int(request.query_params.get("page_size"), 10), 200)
        keyword = (request.query_params.get("search") or "").strip().lower()
        category_id = request.query_params.get("category_id")
        brand_id = request.query_params.get("brand_id")
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")
        sort_by = request.query_params.get("sort_by")
        flash_sale = request.query_params.get("flash_sale")

        try:
            version = redis_client.get("product_list_version") or "1"
            cache_key = f"product:list:v{version}:{page}:{page_size}:{keyword or 'all'}:{category_id}:{brand_id}:{min_price}:{max_price}:{sort_by}"
            cached_data = redis_client.get(cache_key)
            if cached_data:
                return Response(json.loads(cached_data))
        except Exception:
            cache_key = None

        if flash_sale in ("true", "1", "yes"):
            objs = _prod_svc.list_flash_sale()
        else:
            objs = _prod_svc.list()

        if category_id:
            objs = objs.filter(category_id=category_id)
        if brand_id:
            objs = objs.filter(brand_id=brand_id)
        if min_price:
            try:
                objs = objs.filter(price__gte=float(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                objs = objs.filter(price__lte=float(max_price))
            except ValueError:
                pass
                
        if sort_by == 'price_asc':
            objs = objs.order_by('price')
        elif sort_by == 'price_desc':
            objs = objs.order_by('-price')
        elif sort_by == 'newest':
            objs = objs.order_by('-created_at')
        else:
            objs = objs.order_by("id")
        
        data = list(ProductSerializer(objs, many=True).data)
        if keyword:
            data = [
                item for item in data
                if any(keyword in str(value).lower() for value in item.values() if value is not None)
            ]
            
        total = len(data)
        total_pages = max(1, (total + page_size - 1) // page_size)
        if page > total_pages:
            page = total_pages
        start = (page - 1) * page_size
        end = start + page_size
        
        response_data = {
            "count": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "results": data[start:end],
        }
        
        try:
            redis_client.set(cache_key, json.dumps(response_data), ex=180) # 3 mins cache
        except Exception:
            pass
            
        return Response(response_data)

    @require_staff
    def post(self, request):
        try:
            p = _prod_svc.create(request.data)
            return Response(ProductSerializer(p).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ProductDetailView(APIView):
    def get(self, request, pk):
        cache_key = f"product:{pk}"
        try:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                return Response(json.loads(cached_data))
        except Exception:
            pass

        try:
            p = _prod_svc.get(pk)
            data = ProductSerializer(p).data
            try:
                redis_client.set(cache_key, json.dumps(data), ex=600) # 10 mins cache
            except Exception:
                pass
            return Response(data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @require_staff
    def put(self, request, pk):
        try:
            p = _prod_svc.update(pk, request.data)
            return Response(ProductSerializer(p).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class InternalReserveStockView(APIView):
    @require_internal
    def post(self, request):
        """
        POST body: {"order_id": 123, "items": [{"product_id": 1, "quantity": 2}]}
        """
        try:
            order_id = request.data.get("order_id", 0)
            items = request.data.get("items", [])
            _prod_svc.reserve_stock(order_id, items)
            return Response({"message": "Stock reserved successfully"})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class InternalReleaseStockView(APIView):
    @require_internal
    def post(self, request):
        try:
            order_id = request.data.get("order_id", 0)
            items = request.data.get("items", [])
            _prod_svc.release_stock(order_id, items)
            return Response({"message": "Stock released successfully"})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InternalSyncFlashSalesView(APIView):
    @require_internal
    def post(self, request):
        result = _prod_svc.sync_flash_sales_from_promotion()
        return Response(result)

class CategoryListView(APIView):
    def get(self, request):
        objs = _cat_svc.list()
        return Response(CategorySerializer(objs, many=True).data)
        
    @require_staff
    def post(self, request):
        try:
            c = _cat_svc.create(request.data)
            return Response(CategorySerializer(c).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CategoryDetailView(APIView):
    def get(self, request, pk):
        try:
            c = _cat_svc.get(pk)
            return Response(CategorySerializer(c).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @require_staff
    def put(self, request, pk):
        try:
            c = _cat_svc.update(pk, request.data)
            return Response(CategorySerializer(c).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class BrandListView(APIView):
    def get(self, request):
        objs = _brand_svc.list()
        return Response(BrandSerializer(objs, many=True).data)

    @require_staff
    def post(self, request):
        try:
            b = _brand_svc.create(request.data)
            return Response(BrandSerializer(b).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class BrandDetailView(APIView):
    def get(self, request, pk):
        try:
            b = _brand_svc.get(pk)
            return Response(BrandSerializer(b).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @require_staff
    def put(self, request, pk):
        try:
            b = _brand_svc.update(pk, request.data)
            return Response(BrandSerializer(b).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ProductVariantListView(APIView):
    @require_staff
    def post(self, request):
        try:
            v = _var_svc.create(request.data)
            return Response(ProductVariantSerializer(v).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ProductVariantDetailView(APIView):
    def get(self, request, pk):
        try:
            v = _var_svc.get(pk)
            return Response(ProductVariantSerializer(v).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @require_staff
    def put(self, request, pk):
        try:
            v = _var_svc.update(pk, request.data)
            return Response(ProductVariantSerializer(v).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @require_staff
    def delete(self, request, pk):
        try:
            _var_svc.delete(pk)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

class InventoryTransactionListView(APIView):
    @require_staff
    def get(self, request):
        qs = InventoryTransaction.objects.select_related('product', 'variant').all()
        return Response(InventoryTransactionSerializer(qs, many=True).data)

    @require_staff
    def post(self, request):
        data = request.data
        serializer = InventoryTransactionSerializer(data=data)
        if serializer.is_valid():
            tx = serializer.save()
            # Cập nhật stock của product / variant tương ứng
            if tx.variant:
                tx.variant.stock = tx.stock_after
                tx.variant.save(update_fields=['stock'])
            if tx.product:
                tx.product.stock = tx.stock_after
                tx.product.save(update_fields=['stock'])
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
