"""Agent modellari (0-to'lqin) — tool-calling AI uchun.

AgentTask · SelectionSet · PendingAction · AgentAuditLog · AgentUsage
"""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import assistant.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('assistant', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AgentTask',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False,
                                        primary_key=True, serialize=False)),
                ('session_key', models.CharField(blank=True, db_index=True, max_length=64)),
                ('goal', models.CharField(db_index=True, max_length=40, verbose_name='Maqsad')),
                ('state', models.CharField(blank=True, max_length=40, verbose_name='Holat')),
                ('slots', models.JSONField(blank=True, default=dict, verbose_name="Ma'lumotlar")),
                ('missing', models.JSONField(blank=True, default=list, verbose_name='Yetishmayotgan')),
                ('last_ui_ref', models.CharField(blank=True, max_length=32)),
                ('status', models.CharField(choices=[('active', 'Faol'), ('done', 'Tugallangan'),
                                                     ('abandoned', 'Tashlab ketilgan')],
                                            db_index=True, default='active', max_length=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('user', models.ForeignKey(blank=True, null=True,
                                           on_delete=django.db.models.deletion.CASCADE,
                                           related_name='agent_tasks',
                                           to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Agent vazifasi',
                'verbose_name_plural': 'Agent vazifalari (AI)',
                'db_table': 'assistant_agent_task',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='SelectionSet',
            fields=[
                ('ref', models.CharField(default=assistant.models._token, max_length=32,
                                         primary_key=True, serialize=False)),
                ('session_key', models.CharField(blank=True, db_index=True, max_length=64)),
                ('section', models.CharField(max_length=24)),
                ('items', models.JSONField(default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('task', models.ForeignKey(blank=True, null=True,
                                           on_delete=django.db.models.deletion.CASCADE,
                                           related_name='selections', to='assistant.agenttask')),
                ('user', models.ForeignKey(blank=True, null=True,
                                           on_delete=django.db.models.deletion.CASCADE,
                                           related_name='agent_selections',
                                           to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': "Tanlov ro'yxati",
                'verbose_name_plural': "Tanlov ro'yxatlari (AI)",
                'db_table': 'assistant_selection_set',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PendingAction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False,
                                        primary_key=True, serialize=False)),
                ('section', models.CharField(max_length=24)),
                ('action', models.CharField(max_length=40)),
                ('payload', models.JSONField(default=dict)),
                ('summary_card', models.JSONField(blank=True, default=dict)),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('status', models.CharField(choices=[('pending', 'Tasdiq kutilmoqda'),
                                                     ('confirmed', 'Tasdiqlangan'),
                                                     ('cancelled', 'Bekor qilingan'),
                                                     ('expired', "Muddati o'tgan"),
                                                     ('failed', 'Xatolik')],
                                            db_index=True, default='pending', max_length=12)),
                ('result', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('confirmed_at', models.DateTimeField(blank=True, null=True)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('task', models.ForeignKey(blank=True, null=True,
                                           on_delete=django.db.models.deletion.SET_NULL,
                                           related_name='pending_actions',
                                           to='assistant.agenttask')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                           related_name='agent_pending_actions',
                                           to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Tasdiq kutayotgan amal',
                'verbose_name_plural': 'Tasdiq kutayotgan amallar (AI)',
                'db_table': 'assistant_pending_action',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AgentAuditLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True,
                                        serialize=False, verbose_name='ID')),
                ('session_key', models.CharField(blank=True, max_length=64)),
                ('task_id', models.UUIDField(blank=True, null=True)),
                ('section', models.CharField(db_index=True, max_length=24)),
                ('action', models.CharField(db_index=True, max_length=40)),
                ('params', models.JSONField(blank=True, default=dict)),
                ('result_status', models.CharField(choices=[('ok', 'Muvaffaqiyat'),
                                                            ('denied', "Vakolat yo'q"),
                                                            ('limited', 'Limit oshdi'),
                                                            ('error', 'Xatolik'),
                                                            ('pending', 'Tasdiqqa yuborildi')],
                                                   db_index=True, default='ok', max_length=10)),
                ('error', models.CharField(blank=True, max_length=300)),
                ('duration_ms', models.PositiveIntegerField(default=0)),
                ('llm_model', models.CharField(blank=True, max_length=60)),
                ('tokens_in', models.PositiveIntegerField(default=0)),
                ('tokens_out', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('user', models.ForeignKey(blank=True, null=True,
                                           on_delete=django.db.models.deletion.SET_NULL,
                                           related_name='agent_audit_logs',
                                           to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Agent jurnali',
                'verbose_name_plural': 'Agent jurnali (AI)',
                'db_table': 'assistant_agent_audit',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AgentUsage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True,
                                        serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True)),
                ('llm_calls', models.PositiveIntegerField(default=0)),
                ('tool_calls', models.PositiveIntegerField(default=0)),
                ('mutations', models.PositiveIntegerField(default=0)),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                           related_name='agent_usage',
                                           to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Agent kunlik sarfi',
                'verbose_name_plural': 'Agent kunlik sarfi (AI)',
                'db_table': 'assistant_agent_usage',
                'ordering': ['-date'],
                'unique_together': {('user', 'date')},
            },
        ),
        migrations.AddIndex(
            model_name='agenttask',
            index=models.Index(fields=['user', 'status', '-updated_at'],
                               name='agent_task_user_idx'),
        ),
        migrations.AddIndex(
            model_name='pendingaction',
            index=models.Index(fields=['user', 'status', '-created_at'],
                               name='pending_user_status_idx'),
        ),
        migrations.AddIndex(
            model_name='agentauditlog',
            index=models.Index(fields=['user', '-created_at'],
                               name='agent_audit_user_idx'),
        ),
    ]
