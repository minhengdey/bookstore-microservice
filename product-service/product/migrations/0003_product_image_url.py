from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("product", "0002_stockreservationlog"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="image_url",
            field=models.CharField(blank=True, default="", max_length=1000),
        ),
    ]