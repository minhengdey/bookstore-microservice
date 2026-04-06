from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services import BookService
from app.serializers import BookSerializer, BookCreateSerializer
from app.permissions import require_staff

_svc = BookService()


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


class BookListCreateView(APIView):
    def get(self, request):
        """Khách hàng và mọi người đều được xem danh sách sách."""
        search = None
        book_status = request.query_params.get("status")
        books = _svc.list_books(search=search, status=book_status)
        return Response(_paginate_and_search(request, books, BookSerializer))

    @require_staff
    def post(self, request):
        """Chỉ staff/manager được thêm sách."""
        ser = BookCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            book = _svc.create_book(dict(ser.validated_data))
            return Response(BookSerializer(book).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BookDetailView(APIView):
    def get(self, request, pk):
        """Xem chi tiết sách — cho phép mọi người."""
        try:
            book = _svc.get_book(pk)
            return Response(BookSerializer(book).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @require_staff
    def put(self, request, pk):
        try:
            book = _svc.update_book(pk, dict(request.data))
            return Response(BookSerializer(book).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    @require_staff
    def delete(self, request, pk):
        try:
            _svc.delete_book(pk)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
