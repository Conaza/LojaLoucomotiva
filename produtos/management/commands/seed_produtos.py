from django.core.management.base import BaseCommand
from django.db import transaction

from produtos.models import Produto, ProdutoTamanho, Tamanho


SEED = [
    {
        'nome': 'Camisa',
        'slug': 'camisa',
        'descricao': 'Camisa atlética confortável para o dia a dia.',
        'preco': '79.90',
        'tamanhos': [Tamanho.P, Tamanho.M, Tamanho.G, Tamanho.GG],
    },
    {
        'nome': 'Boné',
        'slug': 'bone',
        'descricao': 'Boné ajustável com visual limpo.',
        'preco': '49.90',
        'tamanhos': [Tamanho.UNICO],
    },
    {
        'nome': 'Short',
        'slug': 'short',
        'descricao': 'Short leve, ideal para treinos leves e passeios.',
        'preco': '69.90',
        'tamanhos': [Tamanho.P, Tamanho.M, Tamanho.G],
    },
    {
        'nome': 'Moletom',
        'slug': 'moletom',
        'descricao': 'Moletom macio para dias mais frios.',
        'preco': '129.90',
        'tamanhos': [Tamanho.M, Tamanho.G, Tamanho.GG, Tamanho.XG],
    },
]


class Command(BaseCommand):
    help = 'Cria produtos de exemplo (Camisa, Boné, Short, Moletom).'

    @transaction.atomic
    def handle(self, *args, **options):
        for data in SEED:
            produto, created = Produto.objects.update_or_create(
                slug=data['slug'],
                defaults={
                    'nome': data['nome'],
                    'descricao': data['descricao'],
                    'preco': data['preco'],
                    'ativo': True,
                },
            )
            for tamanho in data['tamanhos']:
                ProdutoTamanho.objects.update_or_create(
                    produto=produto,
                    tamanho=tamanho,
                    defaults={'disponivel': True},
                )
            action = 'Criado' if created else 'Atualizado'
            self.stdout.write(self.style.SUCCESS(f'{action}: {produto.nome}'))
