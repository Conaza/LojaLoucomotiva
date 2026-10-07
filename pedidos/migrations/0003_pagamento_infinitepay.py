import django.db.models.deletion
from django.db import migrations, models


def expirados_para_pendente(apps, schema_editor):
    Pagamento = apps.get_model('pedidos', 'Pagamento')
    Pagamento.objects.filter(status='EXPIRADO').update(status='PENDENTE')


class Migration(migrations.Migration):

    dependencies = [
        ('pedidos', '0002_cobrancapix'),
    ]

    operations = [
        migrations.RenameModel('CobrancaPix', 'Pagamento'),
        migrations.AlterModelOptions(
            name='pagamento',
            options={
                'ordering': ['-criado_em'],
                'verbose_name': 'Pagamento',
                'verbose_name_plural': 'Pagamentos',
            },
        ),
        migrations.RenameField('pagamento', 'txid', 'order_nsu'),
        migrations.RemoveField('pagamento', 'copia_e_cola'),
        migrations.RemoveField('pagamento', 'qr_code_base64'),
        migrations.RemoveField('pagamento', 'expira_em'),
        migrations.AlterField(
            model_name='pagamento',
            name='pedido',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='pagamentos',
                to='pedidos.pedido',
            ),
        ),
        migrations.AddField(
            model_name='pagamento',
            name='checkout_url',
            field=models.URLField(blank=True, default='', max_length=500),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='pagamento',
            name='slug',
            field=models.CharField(blank=True, default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='pagamento',
            name='transaction_nsu',
            field=models.CharField(blank=True, default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='pagamento',
            name='capture_method',
            field=models.CharField(blank=True, default='', max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='pagamento',
            name='receipt_url',
            field=models.URLField(blank=True, default='', max_length=500),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='pagamento',
            name='valor_pago',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.RunPython(expirados_para_pendente, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='pagamento',
            name='status',
            field=models.CharField(
                choices=[('PENDENTE', 'Aguardando pagamento'), ('PAGO', 'Pago')],
                default='PENDENTE',
                max_length=10,
            ),
        ),
    ]
