class AuthError(Exception):
    status_code = 400

    def __init__(self, message: str, status_code: int | None = None, detail=None):
        super().__init__(message)
        self.message = message
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code


class ValidationError(AuthError):
    status_code = 400


class InvalidCredentials(AuthError):
    status_code = 401


class AccountLocked(AuthError):
    status_code = 423


class TokenValidationError(AuthError):
    status_code = 401


class UpstreamServiceError(AuthError):
    status_code = 502

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        detail=None,
        retryable: bool = True,
    ):
        super().__init__(message, status_code=status_code, detail=detail)
        self.retryable = retryable


class CircuitBreakerOpen(AuthError):
    status_code = 503
