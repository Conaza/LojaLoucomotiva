"""Staff views for product CRUD on the custom admin page."""

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from .forms import ProdutoAdminForm
from .images import (
    add_produto_image,
    delete_produto_media_dir,
    first_produto_image,
    list_produto_gallery,
    remove_produto_image_at,
    replace_produto_image,
    save_produto_images,
)
from .models import Produto, ProdutoTamanho, Tamanho

staff_required = staff_member_required(login_url=settings.LOGIN_URL)


def _sync_tamanhos(produto: Produto, selected: list[str]) -> None:
    selected_set = set(selected)
    valid = {c.value for c in Tamanho}
    selected_set &= valid

    existing = {t.tamanho: t for t in produto.tamanhos.all()}
    for tamanho in valid:
        if tamanho in selected_set:
            obj = existing.get(tamanho)
            if obj:
                if not obj.disponivel:
                    obj.disponivel = True
                    obj.save(update_fields=['disponivel'])
            else:
                ProdutoTamanho.objects.create(
                    produto=produto,
                    tamanho=tamanho,
                    disponivel=True,
                )
        elif tamanho in existing:
            existing[tamanho].delete()


@staff_required
@require_http_methods(['GET', 'POST'])
def produto_criar(request):
    if request.method == 'POST':
        form = ProdutoAdminForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                produto = form.save()
                _sync_tamanhos(produto, form.cleaned_data.get('tamanhos') or [])
                save_produto_images(produto.slug, form.cleaned_data.get('imagens') or [])
            messages.success(request, f'Produto "{produto.nome}" criado.')
            return redirect(f"{reverse('pedidos:admin_lista')}?aba=produtos")
    else:
        form = ProdutoAdminForm()

    return render(request, 'admin_custom/produto_form.html', {
        'form': form,
        'titulo': 'Novo produto',
        'produto': None,
        'galeria': [],
    })


def _bind_gallery_fields(form, slug):
    galeria = list_produto_gallery(slug)
    for img in galeria:
        img['field'] = form[f'substituir_{img["index"]}']
    return galeria


@staff_required
@require_http_methods(['GET', 'POST'])
def produto_editar(request, produto_id):
    produto = get_object_or_404(Produto.objects.prefetch_related('tamanhos'), pk=produto_id)
    gallery_count = len(list_produto_gallery(produto.slug))
    if request.method == 'POST':
        post = request.POST.copy()
        post['slug'] = produto.slug
        form = ProdutoAdminForm(
            post,
            request.FILES,
            instance=produto,
            slug_readonly=True,
            gallery_count=gallery_count,
        )
        if form.is_valid():
            with transaction.atomic():
                produto = form.save()
                _sync_tamanhos(produto, form.cleaned_data.get('tamanhos') or [])
                for index in range(gallery_count):
                    uploaded = form.cleaned_data.get(f'substituir_{index}')
                    if uploaded:
                        replace_produto_image(produto.slug, index, uploaded)
                nova = form.cleaned_data.get('nova_imagem')
                if nova:
                    add_produto_image(produto.slug, nova)
            messages.success(request, f'Produto "{produto.nome}" atualizado.')
            return redirect(f"{reverse('pedidos:admin_lista')}?aba=produtos")
    else:
        form = ProdutoAdminForm(
            instance=produto,
            slug_readonly=True,
            gallery_count=gallery_count,
        )

    return render(request, 'admin_custom/produto_form.html', {
        'form': form,
        'titulo': f'Editar — {produto.nome}',
        'produto': produto,
        'galeria': _bind_gallery_fields(form, produto.slug),
    })


@staff_required
@require_http_methods(['GET', 'POST'])
def produto_excluir(request, produto_id):
    produto = get_object_or_404(Produto, pk=produto_id)
    if request.method == 'POST':
        nome = produto.nome
        slug = produto.slug
        produto.delete()
        delete_produto_media_dir(slug)
        messages.success(request, f'Produto "{nome}" excluído.')
        return redirect(f"{reverse('pedidos:admin_lista')}?aba=produtos")

    return render(request, 'admin_custom/produto_confirm_delete.html', {
        'produto': produto,
        'imagem': first_produto_image(produto.slug),
    })


@staff_required
@require_POST
def produto_imagem_excluir(request, produto_id):
    produto = get_object_or_404(Produto, pk=produto_id)
    raw = (request.POST.get('slot') or '').strip()
    try:
        slot = int(raw)
    except ValueError:
        slot = -1
    if slot >= 0 and remove_produto_image_at(produto.slug, slot):
        messages.success(request, 'Imagem removida.')
    else:
        messages.error(request, 'Não foi possível remover a imagem.')
    return redirect('produtos:admin_editar', produto_id=produto.id)
