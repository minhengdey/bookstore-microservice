from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0004_seed_mock_payment'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentOutbox',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('aggregate_id', models.CharField(max_length=255)),
                ('event_type', models.CharField(max_length=255)),
                ('payload', models.JSONField()),
                ('status', models.CharField(default='PENDING', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('retry_count', models.IntegerField(default=0)),
                ('error_message', models.TextField(blank=True)),
            ],
            options={
                'db_table': 'payment_outbox',
            },
        ),
    ]
