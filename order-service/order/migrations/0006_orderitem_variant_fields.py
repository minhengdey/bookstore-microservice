from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0005_order_snapshot_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="variant_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="product_name",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="variant_name",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
