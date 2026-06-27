from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery', '0004_order_orderitem'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Kutilmoqda'), ('accepted', 'Qabul qilindi'),
                    ('preparing', 'Tayyorlanmoqda'), ('ready', 'Tayyor'),
                    ('delivered', 'Yetkazildi'), ('cancelled', 'Bekor qilingan'),
                ],
                db_index=True, default='pending', max_length=20,
            ),
        ),
    ]
