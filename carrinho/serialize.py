"""JSON shape for the cart. Prices come from get_cart_lines, never the client."""

from produtos.images import first_produto_image

from . import cart


def _money(value) -> str:
    return f'{value:.2f}'


def cart_payload(session) -> dict:
    dados = cart.get_cart_lines(session)
    lines = []
    for line in dados['lines']:
        lines.append({
            'produto_id': line['produto_id'],
            'nome': line['produto'].nome,
            'tamanho': line['tamanho'],
            'quantidade': line['quantidade'],
            'preco_unitario': _money(line['preco_unitario']),
            'subtotal': _money(line['subtotal']),
            'imagem': first_produto_image(line['produto'].slug),
        })
    return {
        'quantidade_total': dados['quantidade_total'],
        'valor_total': _money(dados['valor_total']),
        'vazio': dados['vazio'],
        'lines': lines,
    }
