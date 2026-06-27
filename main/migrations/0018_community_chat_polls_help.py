import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0017_remove_transport_alter_ad_category'),
    ]

    operations = [
        # ── ChatMessage: advanced fields ────────────────────────────────────
        migrations.AddField(
            model_name='chatmessage', name='file',
            field=models.FileField(blank=True, null=True, upload_to='chat_files/%Y/%m/'),
        ),
        migrations.AddField(
            model_name='chatmessage', name='audio',
            field=models.FileField(blank=True, null=True, upload_to='chat_voice/%Y/%m/'),
        ),
        migrations.AddField(
            model_name='chatmessage', name='reply_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='replies', to='main.chatmessage'),
        ),
        migrations.AddField(
            model_name='chatmessage', name='forwarded_from',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='forwards', to='main.chatmessage'),
        ),
        migrations.AddField(
            model_name='chatmessage', name='edited_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='chatmessage', name='is_deleted',
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AddIndex(
            model_name='chatmessage',
            index=models.Index(fields=['room', 'created_at'], name='chat_msg_room_created_idx'),
        ),
        # ── ChatMember: receipts / presence ─────────────────────────────────
        migrations.AddField(
            model_name='chatmember', name='last_read_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name="Oxirgi o'qilgan vaqt"),
        ),
        migrations.AddField(
            model_name='chatmember', name='last_seen_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Oxirgi faollik'),
        ),
        # ── MessageReaction ─────────────────────────────────────────────────
        migrations.CreateModel(
            name='MessageReaction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('emoji', models.CharField(max_length=8)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reactions', to='main.chatmessage')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='message_reactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Reaksiya', 'verbose_name_plural': 'Reaksiyalar',
                'db_table': 'chat_message_reactions', 'unique_together': {('message', 'user', 'emoji')},
            },
        ),
        # ── Polls ───────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='Poll',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('question', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('poll_type', models.CharField(choices=[('single', 'Bitta variant'), ('multiple', 'Bir nechta variant')], default='single', max_length=10)),
                ('is_anonymous', models.BooleanField(default=False, verbose_name='Anonim ovoz berish')),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='polls', to=settings.AUTH_USER_MODEL)),
                ('neighborhood', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='polls', to='main.neighborhood')),
            ],
            options={'verbose_name': "So'rovnoma", 'verbose_name_plural': "So'rovnomalar", 'db_table': 'community_polls', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='PollOption',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=200)),
                ('order', models.PositiveIntegerField(default=0)),
                ('poll', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='options', to='main.poll')),
            ],
            options={'db_table': 'community_poll_options', 'ordering': ['order', 'id']},
        ),
        migrations.CreateModel(
            name='PollVote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('option', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='votes', to='main.polloption')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='poll_votes', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'community_poll_votes', 'unique_together': {('option', 'user')}},
        ),
        migrations.CreateModel(
            name='PollComment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('poll', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='main.poll')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='poll_comments', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'community_poll_comments', 'ordering': ['created_at']},
        ),
        # ── Help Center ─────────────────────────────────────────────────────
        migrations.CreateModel(
            name='HelpRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('kind', models.CharField(choices=[('request', "Yordam so'rayman"), ('offer', 'Yordam taklif qilaman')], default='request', max_length=10)),
                ('category', models.CharField(choices=[('general', 'Umumiy yordam'), ('blood', 'Qon topshirish'), ('lost_found', "Yo'qolgan / topilgan"), ('emergency', 'Favqulodda'), ('elderly', 'Keksalarga yordam'), ('donation', 'Xayriya / ehson'), ('volunteer', "Ko'ngillilik")], db_index=True, default='general', max_length=20)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('location', models.CharField(blank=True, max_length=300)),
                ('latitude', models.FloatField(blank=True, null=True)),
                ('longitude', models.FloatField(blank=True, null=True)),
                ('phone', models.CharField(blank=True, max_length=30)),
                ('image', models.ImageField(blank=True, null=True, upload_to='help/%Y/%m/')),
                ('status', models.CharField(choices=[('open', 'Ochiq'), ('in_progress', 'Jarayonda'), ('resolved', 'Hal qilindi'), ('closed', 'Yopildi')], db_index=True, default='open', max_length=15)),
                ('is_urgent', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='help_requests', to=settings.AUTH_USER_MODEL)),
                ('neighborhood', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='help_requests', to='main.neighborhood')),
            ],
            options={'verbose_name': "Yordam so'rovi", 'verbose_name_plural': "Yordam so'rovlari", 'db_table': 'community_help_requests', 'ordering': ['-is_urgent', '-created_at']},
        ),
        migrations.CreateModel(
            name='HelpVolunteer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.CharField(blank=True, max_length=300)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='volunteers', to='main.helprequest')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='volunteering', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'community_help_volunteers', 'ordering': ['created_at'], 'unique_together': {('request', 'user')}},
        ),
    ]
