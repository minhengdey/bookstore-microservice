from django.db import models


class Publisher(models.Model):
    publisher_name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    website = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "publishers"
        ordering = ["publisher_name"]

    def __str__(self):
        return self.publisher_name
