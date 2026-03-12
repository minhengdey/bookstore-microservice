from rest_framework import serializers
from app.models import Book, BookImage, BookAuthor, BookCategory, BookGenre, BookPublisher, BookCondition, BookLanguage


class BookImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookImage
        fields = ["id", "image_url", "is_primary"]


class BookConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookCondition
        fields = ["id", "format", "format_price", "book_condition"]


class BookLanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookLanguage
        fields = ["id", "language_name"]


class BookAuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookAuthor
        fields = ["author_id"]


class BookCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookCategory
        fields = ["category_id"]


class BookGenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookGenre
        fields = ["genre_id"]


class BookPublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookPublisher
        fields = ["publisher_id"]


class BookSerializer(serializers.ModelSerializer):
    images = BookImageSerializer(many=True, read_only=True)
    conditions = BookConditionSerializer(many=True, read_only=True)
    languages = BookLanguageSerializer(many=True, read_only=True)
    author_ids = serializers.SerializerMethodField()
    category_ids = serializers.SerializerMethodField()
    genre_ids = serializers.SerializerMethodField()
    publisher_ids = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            "id", "title", "isbn", "description", "publication_year", "page_count",
            "list_price", "sale_price", "stock", "status",
            "created_date", "updated_date",
            "images", "conditions", "languages",
            "author_ids", "category_ids", "genre_ids", "publisher_ids",
        ]

    def get_author_ids(self, obj):
        return list(obj.book_authors.values_list("author_id", flat=True))

    def get_category_ids(self, obj):
        return list(obj.book_categories.values_list("category_id", flat=True))

    def get_genre_ids(self, obj):
        return list(obj.book_genres.values_list("genre_id", flat=True))

    def get_publisher_ids(self, obj):
        return list(obj.book_publishers.values_list("publisher_id", flat=True))


class BookCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=500)
    isbn = serializers.CharField(max_length=20, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    publication_year = serializers.IntegerField(required=False, allow_null=True)
    page_count = serializers.IntegerField(required=False, allow_null=True)
    list_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    sale_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    stock = serializers.IntegerField(default=0)
    status = serializers.CharField(max_length=20, required=False)
    author_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    category_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    genre_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    publisher_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    images = serializers.ListField(required=False)
    conditions = serializers.ListField(required=False)
    language_names = serializers.ListField(child=serializers.CharField(), required=False)
