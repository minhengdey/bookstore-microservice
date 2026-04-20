from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ....application.services.product_service import ProductApplicationService
from ....infrastructure.repositories.product_repository_impl import ProductRepositoryImpl
from ..serializers.product_serializer import ProductSerializer

class ProductListCreateAPI(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ProductApplicationService(repository=ProductRepositoryImpl())

    def get(self, request):
        products = self.service.list_products()
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data
        try:
            product = self.service.create_product(
                name=data.get('name'),
                category_id=data.get('category_id'),
                price_amount=data.get('price_amount'),
                sku_value=data.get('sku_value'),
                attributes_data=data.get('attributes', {}),
                description=data.get('description', '')
            )
            serializer = ProductSerializer(product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ProductDetailAPI(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = ProductApplicationService(repository=ProductRepositoryImpl())

    def get(self, request, product_id):
        product = self.service.get_product(product_id)
        if not product:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductSerializer(product)
        return Response(serializer.data)

    def delete(self, request, product_id):
        self.service.delete_product(product_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
