import uuid
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0001_initial'),
    ]

    operations = [
        # ── Venue: joylashuv + to'lov/jarima siyosati ──
        migrations.AddField(
            model_name='venue',
            name='latitude',
            field=models.FloatField(blank=True, null=True, verbose_name='Kenglik',
                                    validators=[django.core.validators.MinValueValidator(-90),
                                                django.core.validators.MaxValueValidator(90)]),
        ),
        migrations.AddField(
            model_name='venue',
            name='longitude',
            field=models.FloatField(blank=True, null=True, verbose_name='Uzunlik',
                                    validators=[django.core.validators.MinValueValidator(-180),
                                                django.core.validators.MaxValueValidator(180)]),
        ),
        migrations.AddField(
            model_name='venue',
            name='prepay_required',
            field=models.BooleanField(default=True, verbose_name="Oldindan to'lov majburiy"),
        ),
        migrations.AddField(
            model_name='venue',
            name='cancel_penalty_percent',
            field=models.PositiveSmallIntegerField(
                default=10, verbose_name='Bekor qilish jarimasi (%)',
                validators=[django.core.validators.MaxValueValidator(15)],
                help_text='Bekor qilinsa yoki kelmasa ushlab qolinadigan foiz (max 15%).'),
        ),
        migrations.AddField(
            model_name='venue',
            name='grace_minutes',
            field=models.PositiveSmallIntegerField(
                default=15, verbose_name='Kutish vaqti (daqiqa)',
                help_text='Belgilangan vaqtdan keyin shu daqiqa kutiladi, kelmasa "kelmadi" bo\'ladi.'),
        ),
        # ── VenueService ──
        migrations.CreateModel(
            name='VenueService',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False,
                                        primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=150, verbose_name='Xizmat nomi')),
                ('price', models.BigIntegerField(verbose_name="Narx (so'm)")),
                ('duration_minutes', models.PositiveIntegerField(default=30, verbose_name='Davomiyligi (daqiqa)')),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('venue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                            related_name='services', to='booking.venue')),
            ],
            options={
                'verbose_name': 'Xizmat', 'verbose_name_plural': 'Xizmatlar',
                'db_table': 'venue_services', 'ordering': ['order', 'price'],
            },
        ),
        # ── VenueStaff ──
        migrations.CreateModel(
            name='VenueStaff',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False,
                                        primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=120, verbose_name='Ism')),
                ('specialty', models.CharField(blank=True, max_length=120, verbose_name='Mutaxassisligi')),
                ('photo', models.ImageField(blank=True, null=True, upload_to='venues/staff/%Y/%m/')),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('venue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                            related_name='staff', to='booking.venue')),
            ],
            options={
                'verbose_name': 'Ishchi / usta', 'verbose_name_plural': 'Ishchilar / ustalar',
                'db_table': 'venue_staff', 'ordering': ['order', 'name'],
            },
        ),
        # ── VenueBooking: xizmat/usta + to'lov/jarima maydonlari ──
        migrations.AddField(
            model_name='venuebooking',
            name='service',
            field=models.ForeignKey(blank=True, null=True,
                                    on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='bookings', to='booking.venueservice',
                                    verbose_name='Xizmat'),
        ),
        migrations.AddField(
            model_name='venuebooking',
            name='staff',
            field=models.ForeignKey(blank=True, null=True,
                                    on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='bookings', to='booking.venuestaff',
                                    verbose_name='Usta/ishchi'),
        ),
        migrations.AddField(
            model_name='venuebooking',
            name='paid_amount',
            field=models.BigIntegerField(default=0, verbose_name="To'langan summa"),
        ),
        migrations.AddField(
            model_name='venuebooking',
            name='penalty_amount',
            field=models.BigIntegerField(default=0, verbose_name='Ushlab qolingan jarima'),
        ),
        migrations.AddField(
            model_name='venuebooking',
            name='refund_amount',
            field=models.BigIntegerField(default=0, verbose_name='Qaytariladigan summa'),
        ),
        migrations.AddField(
            model_name='venuebooking',
            name='cancelled_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='venuebooking',
            name='status',
            field=models.CharField(
                choices=[('pending', 'Kutilmoqda'), ('confirmed', 'Tasdiqlangan'),
                         ('completed', 'Yakunlangan'), ('cancelled', 'Bekor qilingan'),
                         ('no_show', 'Kelmadi')],
                db_index=True, default='pending', max_length=20),
        ),
    ]
