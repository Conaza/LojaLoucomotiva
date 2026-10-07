import json
from decimal import Decimal
from io import BytesIO, StringIO
from unittest import mock

import requests
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from openpyxl import load_workbook

from carrinho import cart
from produtos.models import Produto, ProdutoTamanho

from . import infinitepay
from .infinitepay import InfinitePayError
from .models import FormaPagamento, ItemPedido, Pagamento, Pedido, StatusPagamento


class AdminPedidosExcelTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser(
            username='staff',
            email='staff@example.com',
            password='password12345',
        )
        self.client.force_login(user)
        produto = Produto.objects.create(
            nome='Camisa',
            preco='80.00',
            slug='camisa',
        )
        pedido = Pedido.objects.create(
            nome_cliente='Ana',
            contato='11999999999',
            forma_pagamento=FormaPagamento.PIX,
            valor_total='80.00',
        )
        ItemPedido.objects.create(
            pedido=pedido,
            produto=produto,
            nome_produto='Camisa',
            tamanho='M',
            quantidade=1,
            preco_unitario='80.00',
            subtotal='80.00',
        )

    def test_lista_mostra_botao_exportar(self):
        response = self.client.get(reverse('pedidos:admin_lista'))
        self.assertContains(response, reverse('pedidos:admin_excel'))
        self.assertContains(response, 'Exportar Excel')

    def test_excel_baixa_planilha_dos_pedidos(self):
        response = self.client.get(reverse('pedidos:admin_excel'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertIn('pedidos.xlsx', response['Content-Disposition'])
        sheet = load_workbook(BytesIO(response.content)).active
        self.assertEqual(
            [cell.value for cell in sheet[1]],
            [
                'Nome', 'Contato', 'Produtos', 'Pagamento',
                'Status pagamento', 'Data', 'Valor total',
            ],
        )
        self.assertEqual(sheet['A2'].value, 'Ana')
        self.assertEqual(sheet['B2'].value, '11999999999')
        self.assertEqual(sheet['C2'].value, 'Camisa')
        self.assertEqual(sheet['D2'].value, 'PIX')
        self.assertEqual(sheet['G2'].value, 80)

    def test_visitante_nao_baixa_planilha(self):
        self.client.logout()
        response = self.client.get(reverse('pedidos:admin_excel'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)


WEBHOOK_TOKEN = 'token-de-teste'
CHECKOUT_URL = 'https://checkout.infinitepay.com.br/loucomotiva?lenc=abc'
INFINITEPAY_SETTINGS = {
    'INFINITEPAY_HANDLE': 'loucomotiva',
    'INFINITEPAY_API_URL': 'https://api.checkout.infinitepay.io',
    'INFINITEPAY_WEBHOOK_TOKEN': WEBHOOK_TOKEN,
    'SITE_URL': 'https://loja.exemplo.com',
}


def _resposta(status_code=200, corpo=None):
    corpo = {} if corpo is None else corpo
    return mock.Mock(
        ok=200 <= status_code < 300,
        status_code=status_code,
        text=json.dumps(corpo),
        json=mock.Mock(return_value=corpo),
    )


class InfinitePayFake:
    """Simula a API da InfinitePay no lugar de `requests.post`."""

    def __init__(self):
        self.link = _resposta(corpo={'url': CHECKOUT_URL})
        self.check = _resposta(corpo={
            'success': True,
            'paid': True,
            'amount': 16000,
            'paid_amount': 16000,
            'installments': 1,
            'capture_method': 'pix',
        })
        self.chamadas = []

    def __call__(self, url, json=None, **kwargs):
        self.chamadas.append((url, json))
        if url.endswith('/links'):
            return self.link
        if url.endswith('/payment_check'):
            return self.check
        raise AssertionError(f'Chamada inesperada à InfinitePay: {url}')

    def payloads(self, sufixo):
        return [payload for url, payload in self.chamadas if url.endswith(sufixo)]


@override_settings(**INFINITEPAY_SETTINGS)
class PagamentoInfinitePayTests(TestCase):
    def setUp(self):
        self.api = InfinitePayFake()
        patcher = mock.patch('pedidos.infinitepay.requests.post', side_effect=self.api)
        patcher.start()
        self.addCleanup(patcher.stop)

        produto = Produto.objects.create(nome='Camisa', preco='80.00', slug='camisa')
        ProdutoTamanho.objects.create(produto=produto, tamanho='M')
        session = self.client.session
        cart.add_item(session, produto.id, 'M', 2)
        session.save()

    def _finalizar(self, forma=FormaPagamento.PIX):
        return self.client.post(reverse('pedidos:finalizar'), {
            'nome': 'Ana',
            'contato': '11999999999',
            'forma_pagamento': forma,
        })

    def _pedido(self):
        self._finalizar()
        pedido = Pedido.objects.get()
        return pedido, pedido.pagamento_atual

    def _retorno(self, pedido, pagamento, client=None, **params):
        query = {
            'order_nsu': pagamento.order_nsu,
            'transaction_nsu': 'tx-1',
            'slug': 'slug-1',
            'capture_method': 'pix',
            'receipt_url': 'https://comprovante.infinitepay.io/1',
        }
        query.update(params)
        return (client or self.client).get(
            reverse('pedidos:retorno', args=[pedido.id]), query,
        )

    def _webhook(self, corpo, token=WEBHOOK_TOKEN):
        url = reverse('pedidos:webhook')
        if token is not None:
            url += f'?token={token}'
        return self.client.post(url, data=json.dumps(corpo), content_type='application/json')

    def _corpo_webhook(self, pagamento, **extra):
        corpo = {
            'invoice_slug': 'slug-1',
            'amount': 16000,
            'paid_amount': 16000,
            'installments': 1,
            'capture_method': 'credit_card',
            'transaction_nsu': 'tx-1',
            'order_nsu': pagamento.order_nsu,
            'receipt_url': 'https://comprovante.infinitepay.io/1',
            'items': [],
        }
        corpo.update(extra)
        return corpo

    def test_pix_redireciona_para_checkout(self):
        response = self._finalizar()
        self.assertRedirects(response, CHECKOUT_URL, fetch_redirect_response=False)
        pedido = Pedido.objects.get()
        pagamento = pedido.pagamento_atual
        self.assertEqual(pagamento.status, StatusPagamento.PENDENTE)
        self.assertEqual(pagamento.checkout_url, CHECKOUT_URL)
        self.assertTrue(cart.get_cart_lines(self.client.session)['vazio'])

        [payload] = self.api.payloads('/links')
        self.assertEqual(payload, {
            'handle': 'loucomotiva',
            'order_nsu': pagamento.order_nsu,
            'redirect_url': f'https://loja.exemplo.com/pedido/{pedido.id}/pagamento/retorno/',
            'webhook_url': (
                f'https://loja.exemplo.com/pagamentos/infinitepay/webhook/?token={WEBHOOK_TOKEN}'
            ),
            'items': [{'description': 'Camisa (M)', 'quantity': 2, 'price': 8000}],
        })

    def test_cartao_tambem_redireciona_para_checkout(self):
        response = self._finalizar(FormaPagamento.CARTAO)
        self.assertRedirects(response, CHECKOUT_URL, fetch_redirect_response=False)
        self.assertEqual(Pedido.objects.get().forma_pagamento, FormaPagamento.CARTAO)

    @override_settings(SITE_URL='')
    def test_sem_site_url_usa_host_da_requisicao(self):
        self._finalizar()
        [payload] = self.api.payloads('/links')
        self.assertTrue(payload['redirect_url'].startswith('http://testserver/pedido/'))

    def test_erro_da_api_desfaz_pedido_e_mantem_carrinho(self):
        self.api.link = _resposta(400, {'success': False, 'message': 'handle inválido'})
        response = self._finalizar()
        self.assertRedirects(response, reverse('pedidos:finalizar'))
        self.assertFalse(Pedido.objects.exists())
        self.assertFalse(Pagamento.objects.exists())
        self.assertFalse(cart.get_cart_lines(self.client.session)['vazio'])

    def test_url_de_checkout_sem_https_e_rejeitada(self):
        self.api.link = _resposta(corpo={'url': 'http://golpe.example.com'})
        response = self._finalizar()
        self.assertRedirects(response, reverse('pedidos:finalizar'))
        self.assertFalse(Pedido.objects.exists())

    def test_retorno_com_pagamento_confirmado(self):
        pedido, pagamento = self._pedido()
        response = self._retorno(pedido, pagamento)
        self.assertRedirects(response, reverse('pedidos:sucesso', args=[pedido.id]))
        pagamento.refresh_from_db()
        self.assertEqual(pagamento.status, StatusPagamento.PAGO)
        self.assertEqual(pagamento.capture_method, 'pix')
        self.assertEqual(pagamento.transaction_nsu, 'tx-1')
        self.assertEqual(pagamento.slug, 'slug-1')
        self.assertEqual(pagamento.valor_pago, Decimal('160.00'))
        self.assertEqual(pagamento.receipt_url, 'https://comprovante.infinitepay.io/1')
        self.assertIsNotNone(pagamento.pago_em)
        self.assertEqual(self.api.payloads('/payment_check'), [{
            'handle': 'loucomotiva',
            'order_nsu': pagamento.order_nsu,
            'transaction_nsu': 'tx-1',
            'slug': 'slug-1',
        }])

        page = self.client.get(reverse('pedidos:sucesso', args=[pedido.id]))
        self.assertContains(page, 'Pagamento confirmado')
        self.assertContains(page, 'Ver comprovante')

    def test_retorno_com_order_nsu_divergente_nao_confirma(self):
        pedido, pagamento = self._pedido()
        self._retorno(pedido, pagamento, order_nsu='outro')
        pagamento.refresh_from_db()
        self.assertEqual(pagamento.status, StatusPagamento.PENDENTE)
        self.assertEqual(self.api.payloads('/payment_check'), [])

    def test_retorno_com_valor_menor_nao_confirma(self):
        pedido, pagamento = self._pedido()
        self.api.check = _resposta(corpo={
            'success': True, 'paid': True, 'amount': 100, 'paid_amount': 100,
            'capture_method': 'pix',
        })
        self._retorno(pedido, pagamento)
        pagamento.refresh_from_db()
        self.assertEqual(pagamento.status, StatusPagamento.PENDENTE)

    def test_retorno_nao_pago_mantem_pendente(self):
        pedido, pagamento = self._pedido()
        self.api.check = _resposta(corpo={'success': True, 'paid': False, 'amount': 16000})
        response = self._retorno(pedido, pagamento)
        self.assertRedirects(response, reverse('pedidos:sucesso', args=[pedido.id]))
        pagamento.refresh_from_db()
        self.assertEqual(pagamento.status, StatusPagamento.PENDENTE)

        page = self.client.get(reverse('pedidos:sucesso', args=[pedido.id]))
        self.assertContains(page, 'Aguardando a confirmação do pagamento')
        self.assertContains(page, CHECKOUT_URL)
        self.assertContains(page, 'http-equiv="refresh"')

    def test_retorno_com_falha_da_api_nao_quebra(self):
        pedido, pagamento = self._pedido()
        self.api.check = _resposta(500, {'message': 'erro'})
        response = self._retorno(pedido, pagamento)
        self.assertRedirects(response, reverse('pedidos:sucesso', args=[pedido.id]))
        pagamento.refresh_from_db()
        self.assertEqual(pagamento.status, StatusPagamento.PENDENTE)

    def test_retorno_exige_sessao_do_pedido(self):
        pedido, pagamento = self._pedido()
        response = self._retorno(pedido, pagamento, client=self.client_class())
        self.assertEqual(response.status_code, 404)
        pagamento.refresh_from_db()
        self.assertEqual(pagamento.status, StatusPagamento.PENDENTE)

    def test_webhook_valido_marca_como_pago(self):
        _, pagamento = self._pedido()
        response = self._webhook(self._corpo_webhook(pagamento))
        self.assertEqual(response.status_code, 200)
        pagamento.refresh_from_db()
        self.assertEqual(pagamento.status, StatusPagamento.PAGO)
        self.assertEqual(pagamento.capture_method, 'pix')

    def test_webhook_com_token_invalido_retorna_403(self):
        _, pagamento = self._pedido()
        response = self._webhook(self._corpo_webhook(pagamento), token='errado')
        self.assertEqual(response.status_code, 403)
        response = self._webhook(self._corpo_webhook(pagamento), token=None)
        self.assertEqual(response.status_code, 403)
        pagamento.refresh_from_db()
        self.assertEqual(pagamento.status, StatusPagamento.PENDENTE)

    def test_webhook_com_falha_no_payment_check_retorna_400(self):
        _, pagamento = self._pedido()
        self.api.check = _resposta(500, {'message': 'erro'})
        response = self._webhook(self._corpo_webhook(pagamento))
        self.assertEqual(response.status_code, 400)
        pagamento.refresh_from_db()
        self.assertEqual(pagamento.status, StatusPagamento.PENDENTE)

    def test_webhook_nao_confirmado_retorna_200_sem_alterar(self):
        _, pagamento = self._pedido()
        self.api.check = _resposta(404, {'success': False, 'message': 'Not found'})
        response = self._webhook(self._corpo_webhook(pagamento))
        self.assertEqual(response.status_code, 200)
        pagamento.refresh_from_db()
        self.assertEqual(pagamento.status, StatusPagamento.PENDENTE)

    def test_webhook_de_pedido_desconhecido_retorna_200(self):
        _, pagamento = self._pedido()
        response = self._webhook(self._corpo_webhook(pagamento, order_nsu='desconhecido'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.api.payloads('/payment_check'), [])

    def test_webhook_mal_formado_retorna_400(self):
        self._pedido()
        response = self._webhook({'order_nsu': 'x'})
        self.assertEqual(response.status_code, 400)

    def test_webhook_repetido_e_idempotente(self):
        _, pagamento = self._pedido()
        self.assertEqual(self._webhook(self._corpo_webhook(pagamento)).status_code, 200)
        pagamento.refresh_from_db()
        pago_em = pagamento.pago_em
        self.assertEqual(self._webhook(self._corpo_webhook(pagamento)).status_code, 200)
        pagamento.refresh_from_db()
        self.assertEqual(pagamento.pago_em, pago_em)
        self.assertEqual(len(self.api.payloads('/payment_check')), 1)

    def test_marcar_pago_nao_altera_pagamento_ja_pago(self):
        _, pagamento = self._pedido()
        self.assertTrue(pagamento.marcar_pago(capture_method='pix'))
        self.assertFalse(pagamento.marcar_pago(capture_method='credit_card'))
        pagamento.refresh_from_db()
        self.assertEqual(pagamento.capture_method, 'pix')

    def test_command_simula_pagamento(self):
        pedido, pagamento = self._pedido()
        call_command('simular_pagamento', pedido.id, stdout=StringIO())
        pagamento.refresh_from_db()
        self.assertEqual(pagamento.status, StatusPagamento.PAGO)


@override_settings(**INFINITEPAY_SETTINGS)
class InfinitePayClienteTests(SimpleTestCase):
    def test_centavos_arredonda(self):
        self.assertEqual(infinitepay.centavos(Decimal('80.00')), 8000)
        self.assertEqual(infinitepay.centavos(Decimal('19.995')), 2000)
        self.assertEqual(infinitepay.centavos('0.10'), 10)

    @mock.patch('pedidos.infinitepay.requests.post')
    def test_payment_check_404_nao_pago(self, post):
        post.return_value = _resposta(404, {'success': False, 'message': 'Not found'})
        resultado = infinitepay.verificar_pagamento('nsu', 'tx', 'slug')
        self.assertFalse(resultado.pago)

    @mock.patch('pedidos.infinitepay.requests.post')
    def test_payment_check_sem_identificadores_nao_chama_api(self, post):
        self.assertFalse(infinitepay.verificar_pagamento('nsu', '', 'slug').pago)
        post.assert_not_called()

    @mock.patch('pedidos.infinitepay.requests.post')
    def test_falha_de_rede_vira_infinitepay_error(self, post):
        post.side_effect = requests.ConnectionError('sem rede')
        with self.assertRaises(InfinitePayError):
            infinitepay.verificar_pagamento('nsu', 'tx', 'slug')

    @override_settings(INFINITEPAY_HANDLE='')
    @mock.patch('pedidos.infinitepay.requests.post')
    def test_sem_handle_nao_chama_api(self, post):
        with self.assertRaises(InfinitePayError):
            infinitepay.verificar_pagamento('nsu', 'tx', 'slug')
        post.assert_not_called()
