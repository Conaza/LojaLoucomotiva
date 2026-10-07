from django.contrib import admin

from .models import Produto, ProdutoTamanho


class ProdutoTamanhoInline(admin.TabularInline):
    model = ProdutoTamanho
    extra = 1


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco', 'ativo', 'slug')
    list_filter = ('ativo',)
    search_fields = ('nome', 'descricao', 'slug')
    prepopulated_fields = {'slug': ('nome',)}
    inlines = [ProdutoTamanhoInline]


@admin.register(ProdutoTamanho)
class ProdutoTamanhoAdmin(admin.ModelAdmin):
    list_display = ('produto', 'tamanho', 'disponivel')
    list_filter = ('tamanho', 'disponivel')
    search_fields = ('produto__nome',)
