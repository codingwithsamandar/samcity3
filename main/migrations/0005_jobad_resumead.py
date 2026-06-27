import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_booking'),
    ]

    operations = [
        migrations.CreateModel(
            name='JobAd',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('company', models.CharField(max_length=200)),
                ('job_type', models.CharField(
                    choices=[
                        ('full_time', "To'liq stavka"),
                        ('part_time', 'Yarim stavka'),
                        ('remote',    'Masofaviy'),
                        ('contract',  'Shartnoma asosida'),
                        ('temporary', 'Vaqtinchalik'),
                    ],
                    default='full_time',
                    max_length=20,
                )),
                ('salary_min', models.BigIntegerField(blank=True, null=True)),
                ('salary_max', models.BigIntegerField(blank=True, null=True)),
                ('location', models.CharField(blank=True, max_length=200)),
                ('description', models.TextField()),
                ('requirements', models.TextField(blank=True)),
                ('deadline', models.DateField(blank=True, null=True)),
                ('status', models.CharField(
                    choices=[
                        ('active',  'Faol'),
                        ('closed',  'Yopilgan'),
                        ('deleted', "O'chirilgan"),
                    ],
                    db_index=True,
                    default='active',
                    max_length=20,
                )),
                ('views', models.PositiveIntegerField(default=0)),
                ('contact_phone', models.CharField(blank=True, max_length=20)),
                ('contact_telegram', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='job_ads',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': "Ish e'loni",
                'verbose_name_plural': "Ish e'lonlari",
                'db_table': 'job_ads',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ResumeAd',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('experience', models.CharField(
                    choices=[
                        ('no_exp', 'Tajribasiz'),
                        ('1_year', '1 yilgacha'),
                        ('1_3',    '1–3 yil'),
                        ('3_5',    '3–5 yil'),
                        ('5_plus', '5+ yil'),
                    ],
                    default='no_exp',
                    max_length=20,
                )),
                ('salary_min', models.BigIntegerField(blank=True, null=True)),
                ('location', models.CharField(blank=True, max_length=200)),
                ('skills', models.TextField(blank=True)),
                ('about', models.TextField()),
                ('status', models.CharField(
                    choices=[
                        ('active',  'Faol'),
                        ('hired',   'Ishga joylashdi'),
                        ('deleted', "O'chirilgan"),
                    ],
                    db_index=True,
                    default='active',
                    max_length=20,
                )),
                ('views', models.PositiveIntegerField(default=0)),
                ('contact_phone', models.CharField(blank=True, max_length=20)),
                ('contact_telegram', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='resume_ads',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Resume',
                'verbose_name_plural': 'Resumelar',
                'db_table': 'resume_ads',
                'ordering': ['-created_at'],
            },
        ),
    ]
