from rest_framework import serializers
from app.models import BookReview


class BookReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookReview
        fields = "__all__"
        read_only_fields = ["id", "created_date", "status"]
