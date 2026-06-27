# Generated manually 2026-06-12 — Fix related_name clash

from django.db import migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('main', '0013_chat_admin_member_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='groups',
            field=__import__('django.db.models', fromlist=['ManyToManyField']).ManyToManyField(
                blank=True,
                help_text='The groups this user belongs to.',
                related_name='main_user_set',
                related_query_name='main_user',
                to='auth.group',
                verbose_name='groups',
            ),
        ),
        migrations.AlterField(
            model_name='user',
            name='user_permissions',
            field=__import__('django.db.models', fromlist=['ManyToManyField']).ManyToManyField(
                blank=True,
                help_text='Specific permissions for this user.',
                related_name='main_user_permissions',
                related_query_name='main_user_perm',
                to='auth.permission',
                verbose_name='user permissions',
            ),
        ),
    ]
