from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from . import cart
from produtos.images import first_produto_image


def ver_carrinho(request):
    dados = cart.get_cart_lines(request.session)
    for line in dados['lines']:
        line['imagem'] = first_produto_image(line['produto'].slug)
    return render(request, 'carrinho/carrinho.html', {'carrinho': dados})


@require_POST
def adicionar(request):
    try:
        cart.add_item(
            request.session,
            request.POST.get('produto_id'),
            request.POST.get('tamanho'),
            request.POST.get('quantidade', 1),
        )
        messages.success(request, 'Produto adicionado ao carrinho.')
    except ValidationError as exc:
        messages.error(request, '; '.join(exc.messages))
    next_url = request.POST.get('next') or 'carrinho:ver'
    if next_url == 'home':
        return redirect('produtos:home')
    return redirect('carrinho:ver')


@require_POST
def atualizar(request):
    try:
        cart.update_qty(
            request.session,
            request.POST.get('produto_id'),
            request.POST.get('tamanho'),
            request.POST.get('quantidade'),
        )
        messages.success(request, 'Quantidade atualizada.')
    except ValidationError as exc:
        messages.error(request, '; '.join(exc.messages))
    return redirect('carrinho:ver')


@require_POST
def remover(request):
    try:
        cart.remove_item(
            request.session,
            request.POST.get('produto_id'),
            request.POST.get('tamanho'),
        )
        messages.success(request, 'Item removido.')
    except ValidationError as exc:
        messages.error(request, '; '.join(exc.messages))
    return redirect('carrinho:ver')
