from django.contrib import admin

from .models import ItemPedido, Pagamento, Pedido


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = (
        'produto', 'nome_produto', 'tamanho',
        'quantidade', 'preco_unitario', 'subtotal',
    )


class PagamentoInline(admin.TabularInline):
    model = Pagamento
    extra = 0
    can_delete = False
    fields = ('order_nsu', 'status', 'capture_method', 'valor_pago', 'criado_em', 'pago_em')
    readonly_fields = fields


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'nome_cliente', 'contato',
        'forma_pagamento', 'valor_total', 'data_criacao',
    )
    list_filter = ('forma_pagamento', 'data_criacao')
    search_fields = ('nome_cliente', 'contato')
    readonly_fields = (
        'nome_cliente', 'contato', 'forma_pagamento',
        'valor_total', 'data_criacao',
    )
    inlines = [ItemPedidoInline, PagamentoInline]


@admin.register(ItemPedido)
class ItemPedidoAdmin(admin.ModelAdmin):
    list_display = (
        'pedido', 'nome_produto', 'tamanho',
        'quantidade', 'preco_unitario', 'subtotal',
    )
    search_fields = ('nome_produto', 'pedido__nome_cliente')


@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display = ('order_nsu', 'pedido', 'status', 'capture_method', 'valor_pago', 'pago_em')
    list_filter = ('status', 'capture_method')
    search_fields = ('order_nsu', 'transaction_nsu', 'slug', 'pedido__nome_cliente')
    readonly_fields = (
        'pedido', 'order_nsu', 'checkout_url', 'slug', 'transaction_nsu',
        'capture_method', 'receipt_url', 'valor_pago', 'criado_em', 'pago_em',
    )
