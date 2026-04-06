from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services import AuthorService, CategoryService, GenreService, PublisherService
from app.serializers import AuthorSerializer, CategorySerializer, GenreSerializer, PublisherSerializer
from app.permissions import require_staff


def _parse_positive_int(value, default):
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


def _paginate_and_search(request, objs, serializer_cls):
    if hasattr(objs, "order_by"):
        objs = objs.order_by("id")
    else:
        objs = sorted(objs, key=lambda x: getattr(x, "id", 0))

    data = list(serializer_cls(objs, many=True).data)
    keyword = (request.query_params.get("search") or "").strip().lower()
    if keyword:
        data = [
            item for item in data
            if any(keyword in str(value).lower() for value in item.values() if value is not None)
        ]

    page = _parse_positive_int(request.query_params.get("page"), 1)
    page_size = min(_parse_positive_int(request.query_params.get("page_size"), 10), 200)
    total = len(data)
    total_pages = max(1, (total + page_size - 1) // page_size)
    if page > total_pages:
        page = total_pages
    start = (page - 1) * page_size
    end = start + page_size
    next_page = page + 1 if page < total_pages else None
    prev_page = page - 1 if page > 1 else None
    return {
        "count": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "next_page": next_page,
        "prev_page": prev_page,
        "results": data[start:end],
    }


def _crud_list_create(request, service, serializer_cls):
    if request.method == "GET":
        objs = service.list() if hasattr(service, "list") else service.list()
        return Response(_paginate_and_search(request, objs, serializer_cls))
    ser = serializer_cls(data=request.data)
    if ser.is_valid():
        obj = service.create(ser.validated_data)
        return Response(serializer_cls(obj).data, status=status.HTTP_201_CREATED)
    return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


def _crud_detail(request, pk, service, serializer_cls):
    try:
        obj = service.get(pk)
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        return Response(serializer_cls(obj).data)
    if request.method in ("PUT", "PATCH"):
        ser = serializer_cls(obj, data=request.data, partial=request.method == "PATCH")
        if ser.is_valid():
            updated = service.update(pk, ser.validated_data)
            return Response(serializer_cls(updated).data)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
    service.delete(pk)
    return Response(status=status.HTTP_204_NO_CONTENT)


# ── Author ────────────────────────────────────────────────────────────────────

_author_svc = AuthorService()


class AuthorListCreateView(APIView):
    def get(self, request):
        return _crud_list_create(request, _author_svc, AuthorSerializer)
    @require_staff
    def post(self, request):
        return _crud_list_create(request, _author_svc, AuthorSerializer)


class AuthorDetailView(APIView):
    def get(self, request, pk): return _crud_detail(request, pk, _author_svc, AuthorSerializer)
    @require_staff
    def put(self, request, pk): return _crud_detail(request, pk, _author_svc, AuthorSerializer)
    @require_staff
    def patch(self, request, pk): return _crud_detail(request, pk, _author_svc, AuthorSerializer)
    @require_staff
    def delete(self, request, pk): return _crud_detail(request, pk, _author_svc, AuthorSerializer)


# ── Category ──────────────────────────────────────────────────────────────────

_cat_svc = CategoryService()


class CategoryListCreateView(APIView):
    def get(self, request): return _crud_list_create(request, _cat_svc, CategorySerializer)
    @require_staff
    def post(self, request): return _crud_list_create(request, _cat_svc, CategorySerializer)


class CategoryDetailView(APIView):
    def get(self, request, pk): return _crud_detail(request, pk, _cat_svc, CategorySerializer)
    @require_staff
    def put(self, request, pk): return _crud_detail(request, pk, _cat_svc, CategorySerializer)
    @require_staff
    def patch(self, request, pk): return _crud_detail(request, pk, _cat_svc, CategorySerializer)
    @require_staff
    def delete(self, request, pk): return _crud_detail(request, pk, _cat_svc, CategorySerializer)


# ── Genre ─────────────────────────────────────────────────────────────────────

_genre_svc = GenreService()


class GenreListCreateView(APIView):
    def get(self, request): return _crud_list_create(request, _genre_svc, GenreSerializer)
    @require_staff
    def post(self, request): return _crud_list_create(request, _genre_svc, GenreSerializer)


class GenreDetailView(APIView):
    def get(self, request, pk): return _crud_detail(request, pk, _genre_svc, GenreSerializer)
    @require_staff
    def put(self, request, pk): return _crud_detail(request, pk, _genre_svc, GenreSerializer)
    @require_staff
    def patch(self, request, pk): return _crud_detail(request, pk, _genre_svc, GenreSerializer)
    @require_staff
    def delete(self, request, pk): return _crud_detail(request, pk, _genre_svc, GenreSerializer)


# ── Publisher ─────────────────────────────────────────────────────────────────

_pub_svc = PublisherService()


class PublisherListCreateView(APIView):
    def get(self, request): return _crud_list_create(request, _pub_svc, PublisherSerializer)
    @require_staff
    def post(self, request): return _crud_list_create(request, _pub_svc, PublisherSerializer)


class PublisherDetailView(APIView):
    def get(self, request, pk): return _crud_detail(request, pk, _pub_svc, PublisherSerializer)
    @require_staff
    def put(self, request, pk): return _crud_detail(request, pk, _pub_svc, PublisherSerializer)
    @require_staff
    def patch(self, request, pk): return _crud_detail(request, pk, _pub_svc, PublisherSerializer)
    @require_staff
    def delete(self, request, pk): return _crud_detail(request, pk, _pub_svc, PublisherSerializer)
