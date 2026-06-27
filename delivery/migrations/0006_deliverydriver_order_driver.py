import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

STATUS = [
    ('pending', 'Kutilmoqda'), ('accepted', 'Qabul qilindi'), ('preparing', 'Tayyorlanmoqda'),
    ('ready', 'Tayyor'), ('assigned', 'Haydovchi biriktirildi'), ('on_the_way', "Yo'lda"),
    ('delivered', 'Yetkazildi'), ('cancelled', 'Bekor qilingan'),
]
VEHICLE = [('foot', '🚶 Piyoda'), ('bike', '🚲 Velosiped'), ('moto', '🏍️ Mototsikl'), ('car', '🚗 Avtomobil')]


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('delivery', '0005_alter_order_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeliveryDriver',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('full_name', models.CharField(max_length=120, verbose_name='Ism familiya')),
                ('phone', models.CharField(max_length=30, verbose_name='Telefon')),
                ('vehicle_type', models.CharField(choices=VEHICLE, default='moto', max_length=10, verbose_name='Transport turi')),
                ('vehicle_number', models.CharField(blank=True, max_length=30, verbose_name='Davlat raqami')),
                ('is_available', models.BooleanField(default=True, verbose_name="Bo'sh (buyurtma qabul qiladi)")),
                ('is_active', models.BooleanField(default=True, verbose_name='Faol')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='delivery_driver', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Yetkazib beruvchi',
                'verbose_name_plural': 'Yetkazib beruvchilar',
                'db_table': 'delivery_drivers',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='order',
            name='assigned_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='driver',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deliveries', to='delivery.deliverydriver', verbose_name='Haydovchi'),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=STATUS, db_index=True, default='pending', max_length=20),
        ),
    ]
