import json

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from produtos.views import storefront_context

from . import cart
from .serialize import cart_payload


def ver_carrinho(request):
    context = storefront_context(request)
    context['abrir_carrinho'] = True
    return render(request, 'produtos/home.html', context)


def _json_body(request):
    raw = request.body.decode('utf-8') if request.body else ''
    if not raw.strip():
        raw = '{}'
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _cart_action(request, action):
    data = _json_body(request)
    if data is None:
        return JsonResponse({'error': 'Requisição inválida.'}, status=400)
    try:
        action(data)
    except ValidationError as exc:
        return JsonResponse({'error': '; '.join(exc.messages)}, status=400)
    return JsonResponse(cart_payload(request.session))


@require_GET
def api_carrinho(request):
    return JsonResponse(cart_payload(request.session))


@require_POST
def api_adicionar(request):
    def action(data):
        cart.add_item(
            request.session,
            data.get('produto_id'),
            data.get('tamanho'),
            data.get('quantidade', 1),
        )

    return _cart_action(request, action)


@require_POST
def api_atualizar(request):
    def action(data):
        cart.update_qty(
            request.session,
            data.get('produto_id'),
            data.get('tamanho'),
            data.get('quantidade'),
        )

    return _cart_action(request, action)


@require_POST
def api_remover(request):
    def action(data):
        cart.remove_item(
            request.session,
            data.get('produto_id'),
            data.get('tamanho'),
        )

    return _cart_action(request, action)


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
