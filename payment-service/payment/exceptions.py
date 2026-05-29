from common.exceptions import BaseServiceException
from rest_framework import status

class PaymentFailed(BaseServiceException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Payment failed."
    default_code = "payment_failed"

class AlreadyPaid(BaseServiceException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Order is already paid."
    default_code = "already_paid"
