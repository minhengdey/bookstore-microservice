import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0003_orderoutbox_index'),
    ]

    operations = [
        migrations.CreateModel(
            name='OutboxEvent',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('aggregate_id', models.UUIDField()),
                ('aggregate_type', models.CharField(max_length=100)),
                ('event_type', models.CharField(max_length=100)),
                ('message_id', models.UUIDField(unique=True)),
                ('payload', models.JSONField()),
                ('status', models.CharField(
                    max_length=20,
                    choices=[('PENDING', 'PENDING'), ('PUBLISHED', 'PUBLISHED'), ('FAILED', 'FAILED')],
                    default='PENDING'
                )),
                ('retry_count', models.PositiveIntegerField(default=0)),
                ('last_error', models.TextField(null=True, blank=True)),
                ('processed_at', models.DateTimeField(null=True, blank=True)),
                ('next_retry_at', models.DateTimeField(null=True, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'order_outboxevent',
                'indexes': [],
            },
        ),
        migrations.CreateModel(
            name='ProcessedMessage',
            fields=[
                ('message_id', models.CharField(max_length=255, primary_key=True, serialize=False)),
                ('processed_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(max_length=50, default='SUCCESS')),
            ],
            options={
                'db_table': 'order_processedmessage',
            },
        ),
        migrations.AddIndex(
            model_name='outboxevent',
            index=models.Index(fields=['status', 'created_at'], name='order_outboxevent_status_idx'),
        ),
    ]
