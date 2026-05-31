from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0002_orderoutbox'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='orderoutbox',
            index=models.Index(fields=['status', 'created_at'], name='order_outbox_status_created_at_idx'),
        ),
    ]
