import hmac
import json
import logging
import uuid
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from openpyxl import Workbook

from carrinho import cart
from produtos.images import first_produto_image
from produtos.models import Produto

from . import infinitepay
from .forms import FinalizarPedidoForm
from .infinitepay import InfinitePayError
from .models import ItemPedido, Pagamento, Pedido, StatusPagamento

logger = logging.getLogger(__name__)

staff_required = staff_member_required(login_url=settings.LOGIN_URL)


def _throttle_ok(session) -> bool:
    """Simple session throttle: max N orders per hour."""
    limit = getattr(settings, 'MAX_PEDIDOS_POR_HORA', 10)
    now = timezone.now()
    stamps = session.get('pedidos_timestamps', [])
    cutoff = (now - timedelta(hours=1)).isoformat()
    stamps = [s for s in stamps if s >= cutoff]
    session['pedidos_timestamps'] = stamps
    session.modified = True
    return len(stamps) < limit


def _record_pedido_timestamp(session):
    stamps = session.get('pedidos_timestamps', [])
    stamps.append(timezone.now().isoformat())
    session['pedidos_timestamps'] = stamps
    session.modified = True


@require_http_methods(['GET', 'POST'])
def finalizar_pedido(request):
    dados = cart.get_cart_lines(request.session)
    if dados['vazio']:
        messages.error(request, 'Seu carrinho está vazio.')
        return redirect('carrinho:ver')

    for line in dados['lines']:
        line['imagem'] = first_produto_image(line['produto'].slug)

    if request.method == 'POST':
        form = FinalizarPedidoForm(request.POST)
        if form.is_valid():
            if not _throttle_ok(request.session):
                messages.error(
                    request,
                    'Muitos pedidos em pouco tempo. Tente novamente mais tarde.',
                )
                return redirect('pedidos:finalizar')

            # Re-read cart from session only — never trust POST product lists.
            dados = cart.get_cart_lines(request.session)
            if dados['vazio']:
                messages.error(request, 'Seu carrinho está vazio.')
                return redirect('carrinho:ver')

            try:
                with transaction.atomic():
                    pedido = Pedido.objects.create(
                        nome_cliente=form.cleaned_data['nome'],
                        contato=form.cleaned_data['contato'],
                        forma_pagamento=form.cleaned_data['forma_pagamento'],
                        valor_total=dados['valor_total'],
                    )
                    for line in dados['lines']:
                        ItemPedido.objects.create(
                            pedido=pedido,
                            produto=line['produto'],
                            nome_produto=line['produto'].nome,
                            tamanho=line['tamanho'],
                            quantidade=line['quantidade'],
                            preco_unitario=line['preco_unitario'],
                            subtotal=line['subtotal'],
                        )
                    pagamento = _criar_pagamento(request, pedido)
            except InfinitePayError:
                logger.exception('Falha ao gerar o link de pagamento da InfinitePay')
                messages.error(
                    request,
                    'Não foi possível gerar o pagamento agora. Tente novamente em instantes.',
                )
                return redirect('pedidos:finalizar')
            except Exception:
                messages.error(
                    request,
                    'Não foi possível salvar o pedido. Tente novamente.',
                )
                return redirect('pedidos:finalizar')

            cart.clear_cart(request.session)
            request.session['ultimo_pedido_id'] = pedido.id
            _record_pedido_timestamp(request.session)
            return redirect(pagamento.checkout_url)
    else:
        form = FinalizarPedidoForm()

    return render(request, 'pedidos/finalizar.html', {
        'form': form,
        'carrinho': dados,
    })


def _url_absoluta(request, path):
    if settings.SITE_URL:
        return settings.SITE_URL.rstrip('/') + path
    return request.build_absolute_uri(path)


def _criar_pagamento(request, pedido):
    pagamento = Pagamento.objects.create(pedido=pedido, order_nsu=uuid.uuid4().hex)
    webhook_path = reverse('pedidos:webhook')
    if settings.INFINITEPAY_WEBHOOK_TOKEN:
        webhook_path += '?' + urlencode({'token': settings.INFINITEPAY_WEBHOOK_TOKEN})
    pagamento.checkout_url = infinitepay.criar_link(
        pedido,
        pagamento,
        redirect_url=_url_absoluta(request, reverse('pedidos:retorno', args=[pedido.id])),
        webhook_url=_url_absoluta(request, webhook_path),
    )
    pagamento.save(update_fields=['checkout_url'])
    return pagamento


def _confirmar_pagamento(pagamento, transaction_nsu, slug, receipt_url=''):
    """Marca como pago somente se a InfinitePay confirmar a transação e o valor."""
    resultado = infinitepay.verificar_pagamento(pagamento.order_nsu, transaction_nsu, slug)
    if not resultado.pago:
        return False
    esperado = infinitepay.centavos(pagamento.pedido.valor_total)
    if resultado.valor_centavos < esperado:
        logger.warning(
            'Pagamento %s com valor %s menor que o esperado %s',
            pagamento.order_nsu, resultado.valor_centavos, esperado,
        )
        return False
    pago_centavos = resultado.valor_pago_centavos or resultado.valor_centavos
    pagamento.marcar_pago(
        slug=slug,
        transaction_nsu=transaction_nsu,
        capture_method=resultado.capture_method,
        receipt_url=receipt_url if str(receipt_url).startswith('https://') else '',
        valor_pago=Decimal(pago_centavos) / 100,
    )
    return True


def _pedido_da_sessao(request, pedido_id, queryset=None):
    if request.session.get('ultimo_pedido_id') != pedido_id:
        raise Http404('Pedido não encontrado.')
    return get_object_or_404(
        queryset if queryset is not None else Pedido.objects.all(),
        pk=pedido_id,
    )


def pedido_sucesso(request, pedido_id):
    pedido = _pedido_da_sessao(
        request, pedido_id, Pedido.objects.prefetch_related('itens'),
    )
    return render(request, 'pedidos/sucesso.html', {
        'pedido': pedido,
        'pagamento': pedido.pagamento_atual,
    })


@require_GET
def pedido_retorno(request, pedido_id):
    """Destino do botão "Continuar" do checkout (redirect_url)."""
    pedido = _pedido_da_sessao(request, pedido_id)
    pagamento = pedido.pagamento_atual
    if pagamento is None:
        raise Http404('Pagamento não encontrado.')
    if (
        pagamento.status == StatusPagamento.PENDENTE
        and request.GET.get('order_nsu') == pagamento.order_nsu
    ):
        try:
            _confirmar_pagamento(
                pagamento,
                transaction_nsu=request.GET.get('transaction_nsu', ''),
                slug=request.GET.get('slug', ''),
                receipt_url=request.GET.get('receipt_url', ''),
            )
        except InfinitePayError:
            logger.warning(
                'Falha ao confirmar o pagamento %s no retorno', pagamento.order_nsu, exc_info=True,
            )
    return redirect('pedidos:sucesso', pedido_id=pedido.id)


@csrf_exempt
@require_POST
def infinitepay_webhook(request):
    token = settings.INFINITEPAY_WEBHOOK_TOKEN
    if token and not hmac.compare_digest(request.GET.get('token', ''), token):
        logger.warning('Webhook da InfinitePay com token inválido')
        return HttpResponseForbidden()
    try:
        corpo = json.loads(request.body)
        order_nsu = str(corpo['order_nsu'])
        transaction_nsu = str(corpo['transaction_nsu'])
        slug = str(corpo['invoice_slug'])
    except (ValueError, KeyError, TypeError):
        logger.warning('Webhook da InfinitePay mal formado')
        return HttpResponseBadRequest()

    pagamento = Pagamento.objects.select_related('pedido').filter(order_nsu=order_nsu).first()
    if pagamento is None:
        logger.warning('Webhook da InfinitePay para order_nsu desconhecido: %s', order_nsu)
        return HttpResponse(status=200)
    if pagamento.status == StatusPagamento.PAGO:
        return HttpResponse(status=200)
    try:
        confirmado = _confirmar_pagamento(
            pagamento, transaction_nsu, slug, receipt_url=corpo.get('receipt_url', ''),
        )
    except InfinitePayError:
        logger.warning(
            'Falha ao confirmar o pagamento %s no webhook', order_nsu, exc_info=True,
        )
        return HttpResponseBadRequest()
    if not confirmado:
        logger.warning('Webhook da InfinitePay não confirmado pelo payment_check: %s', order_nsu)
    return HttpResponse(status=200)


@staff_required
def admin_pedidos(request):
    pedidos = Pedido.objects.prefetch_related('itens').all()
    produtos = Produto.objects.prefetch_related('tamanhos').all()
    produtos_lista = [
        {
            'produto': p,
            'imagem': first_produto_image(p.slug),
            'tamanhos': [
                t.get_tamanho_display()
                for t in p.tamanhos.all()
                if t.disponivel
            ],
        }
        for p in produtos
    ]
    aba = request.GET.get('aba', 'pedidos')
    if aba not in ('pedidos', 'produtos'):
        aba = 'pedidos'
    return render(request, 'admin_custom/pedidos_lista.html', {
        'pedidos': pedidos,
        'produtos_lista': produtos_lista,
        'aba': aba,
    })


@staff_required
@require_GET
def admin_pedidos_excel(request):
    pedidos = Pedido.objects.prefetch_related('itens').all()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Pedidos'
    sheet.append([
        'Nome', 'Contato', 'Produtos', 'Pagamento',
        'Status pagamento', 'Data', 'Valor total',
    ])
    for pedido in pedidos:
        criado = timezone.localtime(pedido.data_criacao).replace(tzinfo=None)
        sheet.append([
            pedido.nome_cliente,
            pedido.contato,
            pedido.nomes_produtos(),
            pedido.get_forma_pagamento_display(),
            pedido.status_pagamento_display(),
            criado,
            pedido.valor_total,
        ])

    buffer = BytesIO()
    workbook.save(buffer)
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="pedidos.xlsx"'
    return response
