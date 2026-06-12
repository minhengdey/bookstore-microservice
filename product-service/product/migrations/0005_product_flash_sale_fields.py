from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("product", "0004_brand_productvariant_inventorytransaction_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="is_flash_sale",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="product",
            name="flash_sale_price",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="product",
            name="flash_sale_name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="product",
            name="flash_sale_ends_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="product",
            name="flash_sale_id",
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
