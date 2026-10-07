"""Session cart helpers. Prices always come from the ORM, never the client."""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError

from produtos.models import Produto, ProdutoTamanho

CART_SESSION_KEY = 'carrinho'
MAX_QTD = getattr(settings, 'MAX_QTD_ITEM', 20)


def _empty_cart():
    return {'items': []}


def get_cart(session):
    cart = session.get(CART_SESSION_KEY)
    if not isinstance(cart, dict) or 'items' not in cart:
        cart = _empty_cart()
        session[CART_SESSION_KEY] = cart
    return cart


def save_cart(session, cart):
    session[CART_SESSION_KEY] = cart
    session.modified = True


def clear_cart(session):
    session[CART_SESSION_KEY] = _empty_cart()
    session.modified = True


def _parse_quantidade(raw) -> int:
    try:
        qtd = int(raw)
    except (TypeError, ValueError):
        raise ValidationError('Quantidade inválida.')
    if qtd < 1 or qtd > MAX_QTD:
        raise ValidationError(f'Quantidade deve ser entre 1 e {MAX_QTD}.')
    return qtd


def add_item(session, produto_id, tamanho, quantidade):
    qtd = _parse_quantidade(quantidade)
    try:
        produto_id = int(produto_id)
    except (TypeError, ValueError):
        raise ValidationError('Produto inválido.')

    produto = Produto.objects.filter(pk=produto_id, ativo=True).first()
    if not produto:
        raise ValidationError('Produto não disponível.')

    tamanho = (tamanho or '').strip()
    if not ProdutoTamanho.objects.filter(
        produto=produto, tamanho=tamanho, disponivel=True
    ).exists():
        raise ValidationError('Tamanho inválido ou indisponível.')

    cart = get_cart(session)
    for item in cart['items']:
        if item['produto_id'] == produto_id and item['tamanho'] == tamanho:
            nova = min(item['quantidade'] + qtd, MAX_QTD)
            item['quantidade'] = nova
            save_cart(session, cart)
            return

    cart['items'].append({
        'produto_id': produto_id,
        'tamanho': tamanho,
        'quantidade': qtd,
    })
    save_cart(session, cart)


def update_qty(session, produto_id, tamanho, quantidade):
    qtd = _parse_quantidade(quantidade)
    try:
        produto_id = int(produto_id)
    except (TypeError, ValueError):
        raise ValidationError('Produto inválido.')
    tamanho = (tamanho or '').strip()

    cart = get_cart(session)
    for item in cart['items']:
        if item['produto_id'] == produto_id and item['tamanho'] == tamanho:
            item['quantidade'] = qtd
            save_cart(session, cart)
            return
    raise ValidationError('Item não encontrado no carrinho.')


def remove_item(session, produto_id, tamanho):
    try:
        produto_id = int(produto_id)
    except (TypeError, ValueError):
        raise ValidationError('Produto inválido.')
    tamanho = (tamanho or '').strip()

    cart = get_cart(session)
    cart['items'] = [
        i for i in cart['items']
        if not (i['produto_id'] == produto_id and i['tamanho'] == tamanho)
    ]
    save_cart(session, cart)


def get_cart_lines(session):
    """
    Resolve session items against the database.
    Drops invalid lines (inactive product / bad size).
    """
    cart = get_cart(session)
    lines = []
    valid_items = []
    total = Decimal('0.00')
    qtd_total = 0

    for raw in cart['items']:
        produto = Produto.objects.filter(pk=raw.get('produto_id'), ativo=True).first()
        if not produto:
            continue
        tamanho = raw.get('tamanho', '')
        if not ProdutoTamanho.objects.filter(
            produto=produto, tamanho=tamanho, disponivel=True
        ).exists():
            continue
        try:
            quantidade = _parse_quantidade(raw.get('quantidade'))
        except ValidationError:
            continue

        subtotal = (produto.preco * quantidade).quantize(Decimal('0.01'))
        lines.append({
            'produto': produto,
            'produto_id': produto.id,
            'tamanho': tamanho,
            'quantidade': quantidade,
            'preco_unitario': produto.preco,
            'subtotal': subtotal,
        })
        valid_items.append({
            'produto_id': produto.id,
            'tamanho': tamanho,
            'quantidade': quantidade,
        })
        total += subtotal
        qtd_total += quantidade

    if valid_items != cart['items']:
        cart['items'] = valid_items
        save_cart(session, cart)

    return {
        'lines': lines,
        'valor_total': total.quantize(Decimal('0.01')),
        'quantidade_total': qtd_total,
        'vazio': len(lines) == 0,
    }
