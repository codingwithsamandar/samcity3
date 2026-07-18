from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='UnansweredQuery',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('normalized', models.CharField(max_length=255, unique=True, verbose_name='Kalit (ichki)')),
                ('text', models.CharField(max_length=1000, verbose_name='Savol')),
                ('count', models.PositiveIntegerField(default=1, verbose_name='Necha marta so‘ralgan')),
                ('resolved', models.BooleanField(default=False, verbose_name='Hal qilingan')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Birinchi marta')),
                ('last_seen', models.DateTimeField(auto_now=True, verbose_name='Oxirgi marta')),
            ],
            options={
                'verbose_name': 'Javobsiz savol',
                'verbose_name_plural': 'Javobsiz savollar (AI)',
                'db_table': 'assistant_unanswered',
                'ordering': ['-count', '-last_seen'],
            },
        ),
    ]
