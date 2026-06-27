from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('places', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='place',
            name='views',
            field=models.PositiveIntegerField(default=0, verbose_name="Ko'rishlar"),
        ),
    ]
