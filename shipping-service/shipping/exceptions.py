from common.exceptions import BaseServiceException
from rest_framework import status

class ShippingNotFound(BaseServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Shipping record not found."
    default_code = "shipping_not_found"

class InvalidTransition(BaseServiceException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid shipping status transition."
    default_code = "invalid_shipping_transition"
