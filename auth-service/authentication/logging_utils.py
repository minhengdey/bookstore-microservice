from contextvars import ContextVar

_request_id_ctx = ContextVar("request_id", default="-")


def set_request_id(request_id: str) -> None:
    _request_id_ctx.set(request_id)


def get_request_id() -> str:
    return _request_id_ctx.get()


class RequestIdFilter:
    def filter(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = get_request_id()
        if not hasattr(record, "service"):
            record.service = "auth-service"
        return True
