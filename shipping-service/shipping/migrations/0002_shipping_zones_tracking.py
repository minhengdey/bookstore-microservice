from django.db import migrations, models


def backfill_tracking_numbers(apps, schema_editor):
    Shipping = apps.get_model("shipping", "Shipping")
    for shipping in Shipping.objects.filter(tracking_number=""):
        shipping.tracking_number = f"SHIP-{shipping.id:08d}"
        shipping.save(update_fields=["tracking_number"])


class Migration(migrations.Migration):

    dependencies = [
        ("shipping", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShippingZone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("city_name", models.CharField(max_length=100, unique=True)),
                ("distance_km", models.FloatField(default=15.0)),
            ],
            options={
                "db_table": "shipping_zones",
            },
        ),
        migrations.AddField(
            model_name="shippingmethod",
            name="estimated_days",
            field=models.PositiveSmallIntegerField(default=5),
        ),
        migrations.AddField(
            model_name="shipping",
            name="tracking_number",
            field=models.CharField(blank=True, max_length=32, unique=True),
        ),
        migrations.RunPython(backfill_tracking_numbers, migrations.RunPython.noop),
    ]
