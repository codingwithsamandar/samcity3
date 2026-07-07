from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0004_venuebooking_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='venuebooking',
            name='reminder_sent_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Eslatma yuborilgan vaqt'),
        ),
    ]
