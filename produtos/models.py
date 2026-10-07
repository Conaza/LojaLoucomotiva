"""Produto and size models."""

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models


class Produto(models.Model):
    nome = models.CharField(max_length=120)
    descricao = models.TextField(blank=True)
    preco = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    ativo = models.BooleanField(default=True)
    slug = models.SlugField(
        max_length=80,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[a-z0-9\-]+$',
                message='Slug deve conter apenas letras minúsculas, números e hífens.',
            )
        ],
        help_text='Identificador da galeria de imagens.',
    )
    galeria_no_banco = models.BooleanField(
        default=False,
        help_text='Quando marcado, a galeria vem do banco, mesmo vazia.',
    )

    class Meta:
        ordering = ['nome']
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'

    def __str__(self):
        return self.nome


class Tamanho(models.TextChoices):
    PP = 'PP', 'PP'
    P = 'P', 'P'
    M = 'M', 'M'
    G = 'G', 'G'
    GG = 'GG', 'GG'
    XG = 'XG', 'XG'
    UNICO = 'Unico', 'Único'


class ProdutoTamanho(models.Model):
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name='tamanhos',
    )
    tamanho = models.CharField(max_length=10, choices=Tamanho.choices)
    disponivel = models.BooleanField(default=True)

    class Meta:
        unique_together = [('produto', 'tamanho')]
        verbose_name = 'Tamanho do produto'
        verbose_name_plural = 'Tamanhos dos produtos'
        ordering = ['produto', 'tamanho']

    def __str__(self):
        return f'{self.produto.nome} — {self.get_tamanho_display()}'


class ProdutoImagem(models.Model):
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name='imagens',
    )
    ordem = models.PositiveSmallIntegerField()
    sufixo = models.CharField(max_length=8)
    conteudo = models.BinaryField()
    atualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['ordem']
        unique_together = [('produto', 'ordem')]
        verbose_name = 'Imagem do produto'
        verbose_name_plural = 'Imagens do produto'

    def __str__(self):
        return f'{self.produto.slug} — {self.ordem + 1:02d}{self.sufixo}'
