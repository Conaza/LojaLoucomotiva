from django.urls import path

from . import admin_views, views

app_name = 'produtos'

urlpatterns = [
    path('', views.home, name='home'),
    path(
        'admin-pedidos/produtos/novo/',
        admin_views.produto_criar,
        name='admin_criar',
    ),
    path(
        'admin-pedidos/produtos/<int:produto_id>/editar/',
        admin_views.produto_editar,
        name='admin_editar',
    ),
    path(
        'admin-pedidos/produtos/<int:produto_id>/excluir/',
        admin_views.produto_excluir,
        name='admin_excluir',
    ),
    path(
        'admin-pedidos/produtos/<int:produto_id>/imagem/excluir/',
        admin_views.produto_imagem_excluir,
        name='admin_imagem_excluir',
    ),
]
