from django.urls import path

from . import views

app_name = 'carrinho'

urlpatterns = [
    path('', views.ver_carrinho, name='ver'),
    path('api/', views.api_carrinho, name='api'),
    path('api/adicionar/', views.api_adicionar, name='api_adicionar'),
    path('api/atualizar/', views.api_atualizar, name='api_atualizar'),
    path('api/remover/', views.api_remover, name='api_remover'),
    path('adicionar/', views.adicionar, name='adicionar'),
    path('atualizar/', views.atualizar, name='atualizar'),
    path('remover/', views.remover, name='remover'),
]
