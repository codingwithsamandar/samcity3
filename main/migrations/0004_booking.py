from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_add_new_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('message', models.TextField(blank=True, verbose_name='Xabar')),
                ('start_date', models.DateField(blank=True, null=True, verbose_name='Boshlanish sanasi')),
                ('end_date', models.DateField(blank=True, null=True, verbose_name='Tugash sanasi')),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Kutilmoqda'),
                        ('confirmed', 'Tasdiqlangan'),
                        ('cancelled', 'Bekor qilindi'),
                        ('completed', 'Yakunlandi'),
                    ],
                    db_index=True,
                    default='pending',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('ad', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='bookings',
                    to='main.ad',
                )),
                ('buyer', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='my_bookings',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('owner', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='received_bookings',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Bron',
                'verbose_name_plural': 'Bronlar',
                'db_table': 'bookings',
                'ordering': ['-created_at'],
            },
        ),
    ]
