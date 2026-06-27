from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery', '0007_driverlocation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Kutilmoqda'),
                    ('accepted', 'Qabul qilindi'),
                    ('preparing', 'Tayyorlanmoqda'),
                    ('ready', 'Tayyor'),
                    ('assigned', 'Haydovchi biriktirildi'),
                    ('picked_up', 'Olib ketildi'),
                    ('on_the_way', "Yo'lda"),
                    ('delivered', 'Yetkazildi'),
                    ('cancelled', 'Bekor qilingan'),
                ],
                db_index=True, default='pending', max_length=20,
            ),
        ),
    ]
