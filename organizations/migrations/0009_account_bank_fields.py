from django.db import migrations, models


def copy_name_to_bank_name(apps, schema_editor):
    Account = apps.get_model('organizations', 'Account')
    for account in Account.objects.all():
        if not account.bank_name:
            account.bank_name = account.name or 'Cuenta'
        if not account.rif:
            account.rif = 'J000000000'
        if not account.account_number:
            account.account_number = '0000000000'
        if not account.holder:
            account.holder = 'Sin titular'
        account.save(update_fields=['bank_name', 'rif', 'account_number', 'holder'])


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0008_alter_transaction_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='account_number',
            field=models.CharField(default='0000000000', max_length=30, verbose_name='Número de cuenta'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='bank_code',
            field=models.CharField(blank=True, max_length=10, verbose_name='Código de banco'),
        ),
        migrations.AddField(
            model_name='account',
            name='bank_name',
            field=models.CharField(default='Cuenta', max_length=255, verbose_name='Banco'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='currency',
            field=models.CharField(
                choices=[('BS', 'Bolívares'), ('USD', 'Dólares')],
                default='BS',
                max_length=3,
                verbose_name='Moneda',
            ),
        ),
        migrations.AddField(
            model_name='account',
            name='holder',
            field=models.CharField(default='Sin titular', max_length=255, verbose_name='Titular'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='rif',
            field=models.CharField(default='J000000000', max_length=15, verbose_name='RIF'),
            preserve_default=False,
        ),
        migrations.RunPython(copy_name_to_bank_name, migrations.RunPython.noop),
    ]
