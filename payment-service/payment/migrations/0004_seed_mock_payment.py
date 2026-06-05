from django.db import migrations

def seed_mock_payment(apps, schema_editor):
    PaymentMethod = apps.get_model('payment', 'PaymentMethod')
    # Create or update the mock payment method
    PaymentMethod.objects.update_or_create(
        id=1,
        defaults={
            'method_name': 'Thanh toán giả lập',
            'description': 'Mô phỏng thanh toán (tự động thành công)',
            'is_active': True
        }
    )
    # Deactivate other methods if they exist to make mock payment the only one
    PaymentMethod.objects.exclude(id=1).update(is_active=False)

class Migration(migrations.Migration):

    dependencies = [
        ('payment', '0003_add_dlqevent'),
    ]

    operations = [
        migrations.RunPython(seed_mock_payment),
    ]
