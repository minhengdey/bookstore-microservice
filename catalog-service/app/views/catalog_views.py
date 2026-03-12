from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services import AuthorService, CategoryService, GenreService, PublisherService
from app.serializers import AuthorSerializer, CategorySerializer, GenreSerializer, PublisherSerializer
from app.permissions import require_staff


def _crud_list_create(request, service, serializer_cls):
    if request.method == "GET":
        search = request.query_params.get("search")
        objs = service.list(search) if hasattr(service, "list") else service.list()
        return Response(serializer_cls(objs, many=True).data)
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
