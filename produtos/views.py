from django.shortcuts import render

from .images import list_produto_images
from .models import Produto


def home(request):
    produtos = Produto.objects.filter(ativo=True).prefetch_related('tamanhos')
    catalogo = []
    for produto in produtos:
        tamanhos = [
            t.tamanho
            for t in produto.tamanhos.all()
            if t.disponivel
        ]
        catalogo.append({
            'produto': produto,
            'imagens': list_produto_images(produto.slug),
            'tamanhos': tamanhos,
        })
    return render(request, 'produtos/home.html', {'catalogo': catalogo})
