from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0006_utilitypayment'),
    ]

    operations = [
        # Booking modeliga yangi maydonlar qo'shamiz
        migrations.AddField(
            model_name='booking',
            name='guests',
            field=models.PositiveIntegerField(default=1, verbose_name='Mehmonlar soni'),
        ),
        migrations.AddField(
            model_name='booking',
            name='total_amount',
            field=models.BigIntegerField(null=True, blank=True, verbose_name="Umumiy summa (so'm)"),
        ),
        migrations.AddField(
            model_name='booking',
            name='platform_fee',
            field=models.BigIntegerField(default=0, verbose_name="Platforma komissiyasi (so'm)"),
        ),
        migrations.AddField(
            model_name='booking',
            name='owner_amount',
            field=models.BigIntegerField(default=0, verbose_name="Egaga o'tkaziladigan summa (so'm)"),
        ),
        migrations.AddField(
            model_name='booking',
            name='payment_status',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('unpaid',    "To'lanmagan"),
                    ('held',      "Platformada ushlab turilgan"),
                    ('released',  "Egaga o'tkazilgan"),
                    ('refunded',  "Qaytarilgan"),
                    ('partial_refund', "Qisman qaytarilgan"),
                ],
                default='unpaid',
                db_index=True,
                verbose_name="To'lov holati",
            ),
        ),
        migrations.AddField(
            model_name='booking',
            name='refund_amount',
            field=models.BigIntegerField(default=0, verbose_name="Qaytarilgan summa (so'm)"),
        ),
        migrations.AddField(
            model_name='booking',
            name='penalty_amount',
            field=models.BigIntegerField(default=0, verbose_name="Jarima summasi (so'm)"),
        ),
        migrations.AddField(
            model_name='booking',
            name='cancelled_by',
            field=models.CharField(
                max_length=10,
                choices=[('buyer', 'Mijoz'), ('owner', 'Egasi')],
                null=True, blank=True,
                verbose_name='Kim bekor qildi',
            ),
        ),
        migrations.AddField(
            model_name='booking',
            name='paid_at',
            field=models.DateTimeField(null=True, blank=True, verbose_name="To'lov vaqti"),
        ),
        # Ad modeliga venue_booking maydoni qo'shamiz
        migrations.AddField(
            model_name='ad',
            name='venue_booking_enabled',
            field=models.BooleanField(default=False, verbose_name='Venue bron tizimi'),
        ),
        migrations.AddField(
            model_name='ad',
            name='venue_price_per_day',
            field=models.BigIntegerField(null=True, blank=True, verbose_name="Narx (kunlik, so'm)"),
        ),
        migrations.AddField(
            model_name='ad',
            name='venue_price_per_hour',
            field=models.BigIntegerField(null=True, blank=True, verbose_name="Narx (soatlik, so'm)"),
        ),
        migrations.AddField(
            model_name='ad',
            name='venue_capacity',
            field=models.PositiveIntegerField(null=True, blank=True, verbose_name='Sig\'imlilik (kishi)'),
        ),
        migrations.AddField(
            model_name='ad',
            name='cancellation_policy',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('flexible',  'Moslashuvchan (1 kun oldin — 100% qaytarish)'),
                    ('moderate',  "O'rtacha (3 kun oldin — 50% qaytarish)"),
                    ('strict',    "Qattiq (7 kun oldin — 25% qaytarish)"),
                ],
                default='moderate',
                verbose_name='Bekor qilish siyosati',
            ),
        ),
    ]
