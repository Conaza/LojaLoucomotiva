from django.shortcuts import render

from carrinho.serialize import cart_payload

from .images import list_produto_images
from .models import Produto


def storefront_context(request):
    produtos = Produto.objects.filter(ativo=True).prefetch_related('tamanhos')
    catalogo_json = []
    for produto in produtos:
        catalogo_json.append({
            'id': produto.id,
            'nome': produto.nome,
            'descricao': produto.descricao,
            'preco': f'{produto.preco:.2f}',
            'tamanhos': [
                t.tamanho
                for t in produto.tamanhos.all()
                if t.disponivel
            ],
            'imagens': list_produto_images(produto.slug),
        })
    return {
        'catalogo_json': catalogo_json,
        'carrinho_json': cart_payload(request.session),
    }


def home(request):
    return render(request, 'produtos/home.html', storefront_context(request))
