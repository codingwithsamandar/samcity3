from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_user_profile_fields'),
    ]

    operations = [
        # Ad model yangi fieldlar
        migrations.AddField(
            model_name='ad',
            name='latitude',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ad',
            name='longitude',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ad',
            name='sold_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='ad',
            name='contact_phone',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='ad',
            name='contact_telegram',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='ad',
            name='contact_instagram',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='ad',
            name='contact_facebook',
            field=models.CharField(blank=True, max_length=100),
        ),
        # Neighborhood
        migrations.CreateModel(
            name='Neighborhood',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'db_table': 'neighborhoods', 'verbose_name': 'Mahalla', 'verbose_name_plural': 'Mahallalar'},
        ),
        # ChatRoom
        migrations.CreateModel(
            name='ChatRoom',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('neighborhood', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='chat_room', to='main.neighborhood')),
            ],
            options={'db_table': 'chat_rooms'},
        ),
        # ChatMessage
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='main.chatroom')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chat_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'chat_messages', 'ordering': ['created_at']},
        ),
    ]
