from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from app.services import ReviewService
from app.serializers import BookReviewSerializer

_svc = ReviewService()


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
        return Response(BookReviewSerializer(reviews, many=True).data)

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
