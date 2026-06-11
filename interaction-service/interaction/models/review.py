from django.db import models
from django.contrib.postgres.fields import ArrayField

class Review(models.Model):
    product_id = models.IntegerField()
    customer_id = models.IntegerField()
    rating = models.IntegerField()
    comment_text = models.TextField(blank=True, null=True)
    image_urls = ArrayField(models.CharField(max_length=1000), blank=True, null=True, default=list)
    verified_purchase = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_hidden = models.BooleanField(default=False)

    class Meta:
        db_table = "reviews"

    def __str__(self):
        return f"Review {self.id} - Product {self.product_id} by Customer {self.customer_id}"
