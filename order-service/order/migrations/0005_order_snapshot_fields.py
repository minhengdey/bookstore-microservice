from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("order", "0004_outboxevent"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="address_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_address_snapshot",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="voucher_code",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
    ]
