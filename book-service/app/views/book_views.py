from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services import BookService
from app.serializers import BookSerializer, BookCreateSerializer
from app.permissions import require_staff

_svc = BookService()


class BookListCreateView(APIView):
    def get(self, request):
        """Khách hàng và mọi người đều được xem danh sách sách."""
        search = request.query_params.get("search")
        book_status = request.query_params.get("status")
        books = _svc.list_books(search=search, status=book_status)
        return Response(BookSerializer(books, many=True).data)

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
