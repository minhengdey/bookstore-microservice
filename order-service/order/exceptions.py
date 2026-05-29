from common.exceptions import BaseServiceException
from rest_framework import status

class OrderNotFound(BaseServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Order not found."
    default_code = "order_not_found"

class InvalidOrderStatus(BaseServiceException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid order status transition."
    default_code = "invalid_order_status"
