from . import cart


def carrinho_resumo(request):
    dados = cart.get_cart_lines(request.session)
    return {
        'carrinho_qtd': dados['quantidade_total'],
    }
