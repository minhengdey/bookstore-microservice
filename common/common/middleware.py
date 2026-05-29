import uuid
import threading
from django.utils.deprecation import MiddlewareMixin

_request_local = threading.local()

def get_request_id():
    return getattr(_request_local, "request_id", None)

class RequestIDMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.request_id = request_id
        _request_local.request_id = request_id

    def process_response(self, request, response):
        if hasattr(request, "request_id"):
            response["X-Request-ID"] = request.request_id
        if hasattr(_request_local, "request_id"):
            del _request_local.request_id
        return response
