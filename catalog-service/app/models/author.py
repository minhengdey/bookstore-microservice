from django.db import models


class Author(models.Model):
    author_name = models.CharField(max_length=255)
    biography = models.TextField(blank=True)
    birth_year = models.IntegerField(null=True, blank=True)
    death_year = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "authors"
        ordering = ["author_name"]

    def __str__(self):
        return self.author_name
