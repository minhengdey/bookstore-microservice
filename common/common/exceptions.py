from rest_framework.exceptions import APIException
from rest_framework import status

class BaseServiceException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Service error occurred."
    default_code = "service_error"

    def __init__(self, detail=None, code=None, status_code=None):
        if detail is not None:
            self.detail = detail
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
