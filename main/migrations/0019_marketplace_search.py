import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0018_community_chat_polls_help'),
    ]

    operations = [
        migrations.AddField(
            model_name='ad', name='contact_count',
            field=models.PositiveIntegerField(default=0, verbose_name="Kontakt ko'rishlar"),
        ),
        migrations.CreateModel(
            name='AdFavorite',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('ad', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorited_by', to='main.ad')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorite_ads', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'ad_favorites', 'ordering': ['-created_at'], 'unique_together': {('ad', 'user')}},
        ),
        migrations.CreateModel(
            name='AdReport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.CharField(choices=[('spam', 'Spam / reklama'), ('scam', 'Firibgarlik'), ('duplicate', "Takroriy e'lon"), ('offensive', 'Nomaqbul kontent'), ('wrong_category', "Noto'g'ri kategoriya"), ('other', 'Boshqa')], default='other', max_length=20)),
                ('detail', models.CharField(blank=True, max_length=500)),
                ('is_resolved', models.BooleanField(db_index=True, default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('ad', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='main.ad')),
                ('reporter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ad_reports', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'ad_reports', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='AdInquiry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('ad', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inquiries', to='main.ad')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ad_inquiries', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'ad_inquiries', 'ordering': ['created_at']},
        ),
        migrations.AddIndex(
            model_name='adinquiry',
            index=models.Index(fields=['ad', 'created_at'], name='ad_inq_ad_created_idx'),
        ),
        migrations.CreateModel(
            name='SearchQuery',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('term', models.CharField(db_index=True, max_length=120, unique=True)),
                ('count', models.PositiveIntegerField(default=1)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'search_queries', 'ordering': ['-count']},
        ),
    ]
