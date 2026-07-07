import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('delivery', '0016_order_delivered_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='DriverReview',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveSmallIntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=5, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)], verbose_name='Baho (1-5)')),
                ('comment', models.CharField(blank=True, max_length=300, verbose_name='Izoh')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('driver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='delivery.deliverydriver')),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='driver_review', to='delivery.order')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='driver_reviews', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Kuryer bahosi',
                'verbose_name_plural': 'Kuryer baholari',
                'db_table': 'delivery_driver_reviews',
                'ordering': ['-created_at'],
            },
        ),
    ]
