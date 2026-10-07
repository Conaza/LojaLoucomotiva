from django.http import Http404, HttpResponse
from django.shortcuts import render

from carrinho.serialize import cart_payload

from .images import list_produto_images, read_produto_image
from .models import Produto


def produto_imagem(request, slug, filename):
    found = read_produto_image(slug, filename)
    if found is None:
        raise Http404
    data, content_type = found
    response = HttpResponse(data, content_type=content_type)
    response['Cache-Control'] = 'public, max-age=86400'
    return response


def storefront_context(request):
    produtos = Produto.objects.filter(ativo=True).prefetch_related('tamanhos', 'imagens')
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
            'imagens': list_produto_images(produto.slug, produto),
        })
    return {
        'catalogo_json': catalogo_json,
        'carrinho_json': cart_payload(request.session),
    }


def home(request):
    return render(request, 'produtos/home.html', storefront_context(request))
