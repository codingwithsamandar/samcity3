# Generated manually — Transport modelini o'chirish + Ad kategoriyalaridan 'kurs' olib tashlash
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0016_alter_user_groups_alter_user_user_permissions'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Transport',
        ),
        migrations.AlterField(
            model_name='ad',
            name='category',
            field=models.CharField(
                choices=[
                    ('uy_joy', 'Uy-joy'), ('ish', 'Ish'), ('avtomobil', 'Avtomobil'),
                    ('qishloq', "Qishloq xo'jaligi"), ('xizmat', 'Xizmat'),
                    ('hayvonlar', 'Hayvonlar'), ('boshqa', 'Boshqa'),
                ],
                db_index=True, max_length=50,
            ),
        ),
    ]
