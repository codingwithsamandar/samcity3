import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False,
                                        primary_key=True, serialize=False)),
                ('provider', models.CharField(
                    choices=[('payme', 'Payme'), ('click', 'Click')],
                    db_index=True, max_length=10)),
                ('provider_transaction_id', models.CharField(db_index=True, max_length=64)),
                ('target_type', models.CharField(max_length=20)),
                ('target_id', models.CharField(db_index=True, max_length=64)),
                ('amount', models.BigIntegerField(verbose_name="Summa (so'm)")),
                ('state', models.IntegerField(db_index=True, default=1)),
                ('reason', models.IntegerField(blank=True, null=True)),
                ('payme_time', models.BigIntegerField(blank=True, null=True)),
                ('performed_at', models.DateTimeField(blank=True, null=True)),
                ('canceled_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': "To'lov tranzaksiyasi",
                'verbose_name_plural': "To'lov tranzaksiyalari",
                'db_table': 'payments_transactions',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='transaction',
            constraint=models.UniqueConstraint(
                fields=('provider', 'provider_transaction_id'),
                name='uniq_provider_tx'),
        ),
    ]
