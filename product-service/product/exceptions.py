from common.exceptions import BaseServiceException
from rest_framework import status

class ProductNotFound(BaseServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Product not found."
    default_code = "product_not_found"

class InsufficientStock(BaseServiceException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Insufficient stock available."
    default_code = "insufficient_stock"
