from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery', '0009_alter_store_latitude_alter_store_logo_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['status', 'driver'], name='order_status_driver_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['user', '-created_at'], name='order_user_created_idx'),
        ),
    ]
