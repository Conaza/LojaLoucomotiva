import json
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from produtos.models import Produto, ProdutoTamanho


class CartApiTests(TestCase):
    def setUp(self):
        self.produto = Produto.objects.create(
            nome='Camisa Kit',
            descricao='Peça do kit',
            preco=Decimal('75.00'),
            slug='camisa-kit',
            ativo=True,
        )
        ProdutoTamanho.objects.create(
            produto=self.produto,
            tamanho='M',
            disponivel=True,
        )
        ProdutoTamanho.objects.create(
            produto=self.produto,
            tamanho='G',
            disponivel=False,
        )

    def _post(self, url_name, payload, client=None, token=None):
        http = client or self.client
        kwargs = {
            'data': json.dumps(payload),
            'content_type': 'application/json',
        }
        if token is not None:
            kwargs['HTTP_X_CSRFTOKEN'] = token
        return http.post(reverse(url_name), **kwargs)

    def test_adicionar_e_total_vem_do_banco(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse('produtos:home'))
        token = client.cookies['csrftoken'].value
        response = self._post(
            'carrinho:api_adicionar',
            {
                'produto_id': self.produto.id,
                'tamanho': 'M',
                'quantidade': 2,
                'preco': '0.01',
            },
            client=client,
            token=token,
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['quantidade_total'], 2)
        self.assertEqual(body['valor_total'], '150.00')
        self.assertEqual(body['lines'][0]['preco_unitario'], '75.00')
        self.assertEqual(body['lines'][0]['subtotal'], '150.00')

        self.produto.preco = Decimal('10.00')
        self.produto.save()
        atualizado = client.get(reverse('carrinho:api'))
        self.assertEqual(atualizado.status_code, 200)
        self.assertEqual(atualizado.json()['valor_total'], '20.00')
        self.assertEqual(atualizado.json()['lines'][0]['preco_unitario'], '10.00')

    def test_quantidade_invalida(self):
        response = self._post(
            'carrinho:api_adicionar',
            {'produto_id': self.produto.id, 'tamanho': 'M', 'quantidade': 0},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Quantidade', response.json()['error'])
        self.assertTrue(self.client.get(reverse('carrinho:api')).json()['vazio'])

    def test_tamanho_indisponivel(self):
        response = self._post(
            'carrinho:api_adicionar',
            {'produto_id': self.produto.id, 'tamanho': 'G', 'quantidade': 1},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('indisponível', response.json()['error'])
        self.assertTrue(self.client.get(reverse('carrinho:api')).json()['vazio'])

    def test_atualizar(self):
        self._post(
            'carrinho:api_adicionar',
            {'produto_id': self.produto.id, 'tamanho': 'M', 'quantidade': 1},
        )
        response = self._post(
            'carrinho:api_atualizar',
            {'produto_id': self.produto.id, 'tamanho': 'M', 'quantidade': 3},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['quantidade_total'], 3)
        self.assertEqual(body['valor_total'], '225.00')

    def test_remover(self):
        self._post(
            'carrinho:api_adicionar',
            {'produto_id': self.produto.id, 'tamanho': 'M', 'quantidade': 1},
        )
        response = self._post(
            'carrinho:api_remover',
            {'produto_id': self.produto.id, 'tamanho': 'M'},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['vazio'])
        self.assertEqual(body['quantidade_total'], 0)
        self.assertEqual(body['valor_total'], '0.00')

    def test_rejeita_sem_csrf(self):
        client = Client(enforce_csrf_checks=True)
        response = self._post(
            'carrinho:api_adicionar',
            {'produto_id': self.produto.id, 'tamanho': 'M', 'quantidade': 1},
            client=client,
        )
        self.assertEqual(response.status_code, 403)
