import uuid
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('taxi', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Car',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('brand', models.CharField(help_text='Masalan: Chevrolet', max_length=60, verbose_name='Marka')),
                ('model', models.CharField(help_text='Masalan: Cobalt', max_length=60, verbose_name='Model')),
                ('color', models.CharField(blank=True, max_length=40, verbose_name='Rangi')),
                ('plate_number', models.CharField(blank=True, max_length=20, verbose_name='Davlat raqami')),
                ('year', models.PositiveIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1980), django.core.validators.MaxValueValidator(2030)], verbose_name='Ishlab chiqarilgan yili')),
                ('seats', models.PositiveSmallIntegerField(default=4, verbose_name="O'rindiqlar soni")),
                ('car_class', models.CharField(choices=[('econom', 'Ekonom'), ('comfort', 'Komfort'), ('comfort_plus', 'Komfort+'), ('business', 'Biznes'), ('minivan', 'Miniven')], default='econom', max_length=20, verbose_name='Tarif')),
                ('has_conditioner', models.BooleanField(default=False, verbose_name='Konditsioner')),
                ('has_baby_seat', models.BooleanField(default=False, verbose_name="Bolalar o'rindig'i")),
                ('allows_pets', models.BooleanField(default=False, verbose_name='Hayvonlar bilan')),
                ('photo', models.ImageField(blank=True, null=True, upload_to='taxi/cars/')),
                ('taxist', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='car', to='taxi.taxist')),
            ],
            options={
                'verbose_name': 'Mashina',
                'verbose_name_plural': 'Mashinalar',
                'db_table': 'taxi_cars',
            },
        ),
        migrations.CreateModel(
            name='Trip',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('point_a', models.CharField(max_length=150, verbose_name='A punkt')),
                ('point_b', models.CharField(max_length=150, verbose_name='B punkt')),
                ('is_delivery', models.BooleanField(default=False, verbose_name='Dostavka buyurtmasi')),
                ('price', models.BigIntegerField(verbose_name="Narx (so'm)")),
                ('status', models.CharField(choices=[('searching', 'Qidirilmoqda'), ('accepted', 'Qabul qilindi'), ('on_way', "Yo'lda"), ('completed', 'Yakunlandi'), ('cancelled', 'Bekor qilindi')], db_index=True, default='accepted', max_length=20)),
                ('payment_method', models.CharField(choices=[('cash', 'Naqd pul'), ('card', 'Bank kartasi')], default='card', max_length=10)),
                ('payment_status', models.CharField(choices=[('unpaid', "To'lanmagan"), ('paid', "To'langan")], db_index=True, default='unpaid', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('passenger', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='taxi_trips', to=settings.AUTH_USER_MODEL)),
                ('route', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='trips', to='taxi.route')),
                ('taxist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='trips', to='taxi.taxist')),
            ],
            options={
                'verbose_name': 'Sayohat',
                'verbose_name_plural': 'Sayohatlar',
                'db_table': 'taxi_trips',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('amount', models.BigIntegerField(verbose_name="Summa (so'm)")),
                ('card_holder', models.CharField(blank=True, max_length=120, verbose_name='Karta egasi')),
                ('card_last4', models.CharField(blank=True, max_length=4, verbose_name='Karta oxirgi 4 raqami')),
                ('card_brand', models.CharField(blank=True, max_length=20, verbose_name='Karta turi')),
                ('status', models.CharField(choices=[('pending', 'Kutilmoqda'), ('paid', "To'langan"), ('failed', 'Xato')], db_index=True, default='pending', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('trip', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='payment', to='taxi.trip')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='taxi_payments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': "To'lov",
                'verbose_name_plural': "To'lovlar",
                'db_table': 'taxi_payments',
                'ordering': ['-created_at'],
            },
        ),
    ]
