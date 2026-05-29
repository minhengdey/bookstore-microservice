from common.exceptions import BaseServiceException
from rest_framework import status

class CartNotFound(BaseServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Cart not found."
    default_code = "cart_not_found"

class InvalidQuantity(BaseServiceException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid quantity provided."
    default_code = "invalid_quantity"
