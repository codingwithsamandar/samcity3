# Generated manually 2026-06-13 — Biznes va Kurslar bo'limlarini olib tashlash

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0014_fix_user_permissions_related_name'),
    ]

    operations = [
        migrations.DeleteModel(
            name='BusinessImage',
        ),
        migrations.DeleteModel(
            name='Review',
        ),
        migrations.DeleteModel(
            name='Business',
        ),
        migrations.DeleteModel(
            name='Course',
        ),
    ]
