from django.urls import path

from . import views

app_name = 'pedidos'

urlpatterns = [
    path('finalizar-pedido/', views.finalizar_pedido, name='finalizar'),
    path('pedido/sucesso/<int:pedido_id>/', views.pedido_sucesso, name='sucesso'),
    path('pedido/<int:pedido_id>/pagamento/retorno/', views.pedido_retorno, name='retorno'),
    path('pagamentos/infinitepay/webhook/', views.infinitepay_webhook, name='webhook'),
    path('admin-pedidos/', views.admin_pedidos, name='admin_lista'),
    path('admin-pedidos/excel/', views.admin_pedidos_excel, name='admin_excel'),
]
