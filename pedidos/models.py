"""Pedido and line-item models."""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone

from produtos.models import Produto


class FormaPagamento(models.TextChoices):
    PIX = 'PIX', 'PIX'
    CARTAO = 'CARTAO', 'Cartão'


class StatusPagamento(models.TextChoices):
    PENDENTE = 'PENDENTE', 'Aguardando pagamento'
    PAGO = 'PAGO', 'Pago'


class Pedido(models.Model):
    nome_cliente = models.CharField(max_length=120)
    contato = models.CharField(
        max_length=40,
        validators=[
            RegexValidator(
                regex=r'^[\d\s\+\(\)\-]+$',
                message='Contato deve conter apenas números e símbolos telefônicos.',
            )
        ],
    )
    forma_pagamento = models.CharField(
        max_length=10,
        choices=FormaPagamento.choices,
    )
    valor_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_criacao']
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'

    def __str__(self):
        return f'Pedido #{self.pk} — {self.nome_cliente}'

    def nomes_produtos(self):
        return ', '.join(self.itens.values_list('nome_produto', flat=True))

    @property
    def pagamento_atual(self):
        return self.pagamentos.order_by('-criado_em').first()

    def status_pagamento_display(self):
        pagamento = self.pagamento_atual
        return pagamento.get_status_display() if pagamento else '—'


class Pagamento(models.Model):
    """Link de checkout da InfinitePay gerado para um pedido."""

    METODOS = {'pix': 'Pix', 'credit_card': 'Cartão de crédito'}

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='pagamentos',
    )
    order_nsu = models.CharField(max_length=64, unique=True)
    checkout_url = models.URLField(max_length=500, blank=True)
    slug = models.CharField(max_length=100, blank=True)
    transaction_nsu = models.CharField(max_length=100, blank=True)
    capture_method = models.CharField(max_length=20, blank=True)
    receipt_url = models.URLField(max_length=500, blank=True)
    valor_pago = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=StatusPagamento.choices,
        default=StatusPagamento.PENDENTE,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    pago_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'

    def __str__(self):
        return f'Pagamento {self.order_nsu} — {self.get_status_display()}'

    def metodo_display(self):
        return self.METODOS.get(self.capture_method, self.capture_method)

    def marcar_pago(self, **dados) -> bool:
        """Marca como pago e guarda os dados da transação.

        Idempotente: retorna False, sem alterar nada, se já estava pago.
        Aceita `slug`, `transaction_nsu`, `capture_method`, `receipt_url` e
        `valor_pago`; valores vazios são ignorados.
        """
        if self.status == StatusPagamento.PAGO:
            return False
        campos = ['status', 'pago_em']
        for campo in ('slug', 'transaction_nsu', 'capture_method', 'receipt_url', 'valor_pago'):
            valor = dados.get(campo)
            if valor not in (None, ''):
                setattr(self, campo, valor)
                campos.append(campo)
        self.status = StatusPagamento.PAGO
        self.pago_em = timezone.now()
        self.save(update_fields=campos)
        return True


class ItemPedido(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='itens',
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itens_pedido',
    )
    nome_produto = models.CharField(max_length=120)
    tamanho = models.CharField(max_length=10)
    quantidade = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(getattr(settings, 'MAX_QTD_ITEM', 20)),
        ]
    )
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = 'Item do pedido'
        verbose_name_plural = 'Itens do pedido'

    def __str__(self):
        return f'{self.nome_produto} ({self.tamanho}) x{self.quantidade}'
