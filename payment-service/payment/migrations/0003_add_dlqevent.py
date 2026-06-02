from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0002_payment_shipping_failure_reason_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DLQEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('queue_name', models.CharField(max_length=255)),
                ('exchange', models.CharField(blank=True, max_length=255)),
                ('routing_key', models.CharField(blank=True, max_length=255)),
                ('body', models.JSONField()),
                ('error_message', models.TextField(blank=True)),
                ('received_at', models.DateTimeField(auto_now_add=True)),
                ('replayed', models.BooleanField(default=False)),
            ],
            options={
                'db_table': 'dlq_events',
            },
        ),
    ]
