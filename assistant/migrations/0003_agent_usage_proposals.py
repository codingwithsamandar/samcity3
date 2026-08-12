"""AgentUsage.proposals — taklif va tasdiqlangan amalni alohida sanash uchun.

Avval `mutations` taklif paytida oshirilardi: 20 ta buyurtma taklif qildirib,
bittasini ham tasdiqlamagan foydalanuvchi kun oxirigacha bloklanardi. Endi
`proposals` (taklif, chegarasi kengroq) va `mutations` (haqiqatda bajarilgan)
alohida hisoblanadi.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0002_agent_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='agentusage',
            name='proposals',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
