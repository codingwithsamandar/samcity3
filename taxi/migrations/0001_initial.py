import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TaxiService',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=150, verbose_name='Nomi')),
                ('short_number', models.CharField(blank=True, db_index=True, help_text='Masalan: 1265, 1187', max_length=10, verbose_name='Qisqa raqam')),
                ('phone', models.CharField(blank=True, max_length=30, verbose_name='Telefon')),
                ('logo', models.ImageField(blank=True, null=True, upload_to='taxi/services/')),
                ('description', models.TextField(blank=True, verbose_name='Tavsif')),
                ('base_price', models.BigIntegerField(default=0, help_text="Mashinaga o'tirish/chaqirish narxi", verbose_name="Boshlang'ich narx (so'm)")),
                ('price_per_km', models.BigIntegerField(default=0, verbose_name="Har km uchun narx (so'm)")),
                ('working_hours', models.CharField(blank=True, default='24/7', max_length=100, verbose_name='Ish vaqti')),
                ('region', models.CharField(blank=True, default='Shofirkon', max_length=100, verbose_name='Hudud')),
                ('is_active', models.BooleanField(default=True, verbose_name='Faol')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Taksi xizmati',
                'verbose_name_plural': 'Taksi xizmatlari',
                'db_table': 'taxi_services',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Taxist',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('full_name', models.CharField(max_length=120, verbose_name='Ism familiya')),
                ('phone', models.CharField(max_length=30, verbose_name='Telefon')),
                ('car_model', models.CharField(blank=True, max_length=120, verbose_name='Mashina turi/modeli')),
                ('photo', models.ImageField(blank=True, null=True, upload_to='taxi/taxists/')),
                ('region', models.CharField(blank=True, default='Shofirkon', max_length=100, verbose_name='Hudud')),
                ('trips_count', models.PositiveIntegerField(default=0, verbose_name="Tashilgan yo'lovchilar soni")),
                ('is_active', models.BooleanField(default=True, verbose_name='Faol')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('service', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='taxists', to='taxi.taxiservice', verbose_name="Bog'liq xizmat (ixtiyoriy)")),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='taxist_profiles', to=settings.AUTH_USER_MODEL, verbose_name='Foydalanuvchi (ixtiyoriy)')),
            ],
            options={
                'verbose_name': 'Taksist',
                'verbose_name_plural': 'Taksistlar',
                'db_table': 'taxi_taxists',
                'ordering': ['-trips_count', 'full_name'],
            },
        ),
        migrations.CreateModel(
            name='Route',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('point_a', models.CharField(max_length=150, verbose_name='A punkt (qayerdan)')),
                ('point_b', models.CharField(max_length=150, verbose_name='B punkt (qayerga)')),
                ('passenger_price', models.BigIntegerField(help_text='Bir kishini A dan B ga olib borish narxi', verbose_name="Yo'lovchi narxi (so'm)")),
                ('delivery_price', models.BigIntegerField(blank=True, help_text='Pochta/yuk yetkazish narxi', null=True, verbose_name="Dostavka narxi (so'm)")),
                ('note', models.CharField(blank=True, max_length=200, verbose_name='Izoh')),
                ('is_active', models.BooleanField(default=True, verbose_name='Faol')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('taxist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='routes', to='taxi.taxist')),
            ],
            options={
                'verbose_name': 'AB marshrut',
                'verbose_name_plural': 'AB marshrutlar',
                'db_table': 'taxi_routes',
                'ordering': ['point_a', 'point_b'],
            },
        ),
        migrations.CreateModel(
            name='ServiceReview',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('rating', models.PositiveSmallIntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=5, verbose_name='Baho (1-5)')),
                ('comment', models.TextField(blank=True, verbose_name='Izoh')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='taxi.taxiservice')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='taxi_service_reviews', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Xizmat sharhi',
                'verbose_name_plural': 'Xizmat sharhlari',
                'db_table': 'taxi_service_reviews',
                'ordering': ['-created_at'],
                'unique_together': {('service', 'user')},
            },
        ),
        migrations.CreateModel(
            name='TaxistReview',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('rating', models.PositiveSmallIntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=5, verbose_name='Baho (1-5)')),
                ('comment', models.TextField(blank=True, verbose_name='Izoh')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('taxist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='taxi.taxist')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='taxist_reviews', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Taksist sharhi',
                'verbose_name_plural': 'Taksist sharhlari',
                'db_table': 'taxi_taxist_reviews',
                'ordering': ['-created_at'],
                'unique_together': {('taxist', 'user')},
            },
        ),
    ]
