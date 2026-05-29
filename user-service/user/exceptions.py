from common.exceptions import BaseServiceException
from rest_framework import status

class UserNotFound(BaseServiceException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "User not found."
    default_code = "user_not_found"

class UnauthorizedAccess(BaseServiceException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "unauthorized_access"
