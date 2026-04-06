from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services import ReviewService
from app.serializers import BookReviewSerializer

_svc = ReviewService()


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


class BookReviewView(APIView):
    """GET /reviews/?book_id=&customer_id=   POST /reviews/"""
    def get(self, request):
        book_id = request.query_params.get("book_id")
        customer_id = request.query_params.get("customer_id")
        if book_id:
            reviews = _svc.list_by_book(int(book_id))
        elif customer_id:
            reviews = _svc.list_by_customer(int(customer_id))
        else:
            reviews = []
        return Response(_paginate_and_search(request, reviews, BookReviewSerializer))

    def post(self, request):
        ser = BookReviewSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            review = _svc.create_review(ser.validated_data)
            return Response(BookReviewSerializer(review).data, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReviewDetailView(APIView):
    def get(self, request, pk):
        try: return Response(BookReviewSerializer(_svc.get(pk)).data)
        except ValueError as e: return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        try: return Response(BookReviewSerializer(_svc.update_review(pk, dict(request.data))).data)
        except ValueError as e: return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try: _svc.delete_review(pk); return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e: return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)


class BookRatingView(APIView):
    """GET /books/<book_id>/rating/ → average rating."""
    def get(self, request, book_id):
        return Response(_svc.get_average_rating(book_id))
