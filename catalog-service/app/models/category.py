from django.db import models


class Category(models.Model):
    category_name = models.CharField(max_length=255)
    parent_category = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="subcategories"
    )
    description = models.TextField(blank=True)

    class Meta:
        db_table = "categories"
        verbose_name_plural = "categories"
        ordering = ["category_name"]

    def __str__(self):
        return self.category_name
