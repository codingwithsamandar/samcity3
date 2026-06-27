import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_jobad_resumead'),
    ]

    operations = [
        migrations.CreateModel(
            name='UtilityPayment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('service', models.CharField(choices=[
                    ('elektr', '⚡ Elektr'),
                    ('suv', '💧 Suv'),
                    ('gaz', '🔥 Gaz'),
                    ('internet', '🌐 Internet'),
                    ('telefon', '📞 Telefon'),
                    ('uy_fondi', '🏘️ Uy-joy fondi'),
                    ('boshqa', '📋 Boshqa'),
                ], max_length=20)),
                ('amount', models.BigIntegerField(verbose_name="Summa (so'm)")),
                ('period', models.CharField(max_length=7, verbose_name='Davr (YYYY-MM)')),
                ('status', models.CharField(choices=[
                    ('tolangan', "To'langan"),
                    ('kutilmoqda', 'Kutilmoqda'),
                    ('muddati_otgan', "Muddati o'tgan"),
                ], default='tolangan', max_length=20)),
                ('note', models.CharField(blank=True, max_length=255, verbose_name='Izoh')),
                ('paid_at', models.DateField(verbose_name="To'lov sanasi")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='utility_payments',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': "Kommunal to'lov",
                'verbose_name_plural': "Kommunal to'lovlar",
                'db_table': 'utility_payments',
                'ordering': ['-paid_at', '-created_at'],
            },
        ),
    ]
