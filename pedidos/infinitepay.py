"""Cliente do checkout hospedado da InfinitePay.

Veja docs/INTEGRACAO_INFINITEPAY.md. O webhook e os parâmetros de retorno não
são autenticados pela InfinitePay; um pagamento só deve ser considerado pago
depois de confirmado por `verificar_pagamento`.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

import requests
from django.conf import settings

TIMEOUT = 10


class InfinitePayError(Exception):
    """Falha de comunicação ou resposta inesperada da InfinitePay."""


@dataclass(frozen=True)
class ResultadoPagamento:
    pago: bool
    valor_centavos: int = 0
    valor_pago_centavos: int = 0
    capture_method: str = ''


def centavos(valor) -> int:
    return int((Decimal(valor) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def _handle() -> str:
    handle = settings.INFINITEPAY_HANDLE.lstrip('$')
    if not handle:
        raise InfinitePayError('INFINITEPAY_HANDLE não configurado.')
    return handle


def _post(path: str, payload: dict) -> requests.Response:
    try:
        return requests.post(
            f'{settings.INFINITEPAY_API_URL.rstrip("/")}{path}',
            json=payload,
            headers={'Accept': 'application/json'},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        raise InfinitePayError(f'Falha de comunicação com a InfinitePay: {exc}') from exc


def _json(resp: requests.Response) -> dict:
    try:
        dados = resp.json()
    except ValueError as exc:
        raise InfinitePayError(f'InfinitePay respondeu {resp.status_code} sem JSON.') from exc
    if not isinstance(dados, dict):
        raise InfinitePayError('Resposta inesperada da InfinitePay.')
    return dados


def _erro(resp: requests.Response) -> InfinitePayError:
    try:
        mensagem = resp.json().get('message', '')
    except (ValueError, AttributeError):
        mensagem = resp.text[:200]
    return InfinitePayError(f'InfinitePay respondeu {resp.status_code}: {mensagem}')


def criar_link(pedido, pagamento, redirect_url: str, webhook_url: str) -> str:
    """Cria o link de checkout e devolve a URL para onde o cliente vai."""
    itens = [
        {
            'description': f'{item.nome_produto} ({item.tamanho})',
            'quantity': item.quantidade,
            'price': centavos(item.preco_unitario),
        }
        for item in pedido.itens.all()
    ]
    if not itens:
        raise InfinitePayError('Pedido sem itens.')
    resp = _post('/links', {
        'handle': _handle(),
        'order_nsu': pagamento.order_nsu,
        'redirect_url': redirect_url,
        'webhook_url': webhook_url,
        'items': itens,
    })
    if not resp.ok:
        raise _erro(resp)
    url = _json(resp).get('url')
    if not isinstance(url, str) or not url.startswith('https://'):
        raise InfinitePayError(f'URL de checkout inválida: {url!r}')
    return url


def verificar_pagamento(order_nsu: str, transaction_nsu: str, slug: str) -> ResultadoPagamento:
    """Consulta na InfinitePay se a transação do pedido foi paga."""
    if not (order_nsu and transaction_nsu and slug):
        return ResultadoPagamento(pago=False)
    resp = _post('/payment_check', {
        'handle': _handle(),
        'order_nsu': order_nsu,
        'transaction_nsu': transaction_nsu,
        'slug': slug,
    })
    if resp.status_code == 404:
        return ResultadoPagamento(pago=False)
    if not resp.ok:
        raise _erro(resp)
    dados = _json(resp)
    try:
        return ResultadoPagamento(
            pago=dados.get('success') is True and dados.get('paid') is True,
            valor_centavos=int(dados.get('amount') or 0),
            valor_pago_centavos=int(dados.get('paid_amount') or 0),
            capture_method=str(dados.get('capture_method') or ''),
        )
    except (TypeError, ValueError) as exc:
        raise InfinitePayError('Resposta inesperada do payment_check.') from exc
