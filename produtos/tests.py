"""Gallery slot behavior for product images."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from produtos.forms import ProdutoAdminForm
from produtos.images import (
    list_produto_gallery,
    list_produto_images,
    remove_produto_image_at,
    replace_produto_image,
    save_produto_images,
)
from produtos.models import Produto, ProdutoImagem

PNG_BYTES = b'\x89PNG\r\n\x1a\n' + b'0' * 16
ONE_MB = b'\x89PNG\r\n\x1a\n' + b'0' * (1024 * 1024 - 8)


def _png(name='foto.png', payload=None):
    body = PNG_BYTES if payload is None else b'\x89PNG\r\n\x1a\n' + payload
    return SimpleUploadedFile(name, body, content_type='image/png')


class ProdutoGalleryTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.static = root / 'static'
        self.media = root / 'media'
        self.static.mkdir()
        self.media.mkdir()
        self.addCleanup(self.tmp.cleanup)
        for target in ('produto_images_base', 'produto_media_base'):
            patcher = patch(
                f'produtos.images.{target}',
                return_value=self.static if target == 'produto_images_base' else self.media,
            )
            patcher.start()
            self.addCleanup(patcher.stop)

    def _static(self, slug, names):
        folder = self.static / slug
        folder.mkdir()
        for name in names:
            (folder / name).write_bytes(f'<svg>{name}</svg>'.encode())

    def _produto(self, slug):
        return Produto.objects.create(
            nome=slug,
            descricao='',
            preco='10.00',
            ativo=True,
            slug=slug,
        )

    def test_gallery_matches_storefront_order(self):
        self._static('camisa', ['imagem2.svg', 'imagem1.svg', 'imagem3.svg'])
        urls = list_produto_images('camisa')
        gallery = list_produto_gallery('camisa')
        names = [url.split('?', 1)[0].rsplit('/', 1)[-1] for url in urls]
        self.assertEqual(names, ['imagem1.svg', 'imagem2.svg', 'imagem3.svg'])
        self.assertEqual([item['name'] for item in gallery], names)
        self.assertEqual([item['url'] for item in gallery], urls)
        self.assertEqual([item['index'] for item in gallery], [0, 1, 2])
        self.assertTrue(all('?v=' in url for url in urls))

    def test_replace_copies_static_and_keeps_other_slots(self):
        self._static('camisa', ['imagem1.svg', 'imagem2.svg', 'imagem3.svg'])
        produto = self._produto('camisa')
        self.assertTrue(replace_produto_image('camisa', 0, _png('nova.png')))
        produto.refresh_from_db()
        self.assertTrue(produto.galeria_no_banco)
        rows = list(produto.imagens.order_by('ordem'))
        self.assertEqual([row.sufixo for row in rows], ['.png', '.svg', '.svg'])
        self.assertEqual(bytes(rows[0].conteudo), PNG_BYTES)
        self.assertIn(b'imagem2.svg', bytes(rows[1].conteudo))
        self.assertTrue((self.static / 'camisa' / 'imagem1.svg').is_file())
        self.assertFalse((self.media / 'camisa').exists())
        urls = list_produto_images('camisa')
        self.assertEqual(len(urls), 3)
        self.assertIn('/media/produtos/camisa/01.png', urls[0])
        self.assertIn('/media/produtos/camisa/02.svg', urls[1])
        self.assertIn('/media/produtos/camisa/03.svg', urls[2])

    def test_remove_renumbers_following_images(self):
        self._static('bone', ['imagem1.svg', 'imagem2.svg'])
        produto = self._produto('bone')
        self.assertTrue(remove_produto_image_at('bone', 0))
        rows = list(produto.imagens.order_by('ordem'))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].sufixo, '.svg')
        self.assertEqual(rows[0].ordem, 0)
        self.assertIn(b'imagem2.svg', bytes(rows[0].conteudo))
        urls = list_produto_images('bone')
        self.assertEqual(len(urls), 1)
        self.assertIn('01.svg', urls[0])

    def test_remove_all_does_not_restore_static(self):
        self._static('short', ['imagem1.svg'])
        produto = self._produto('short')
        self.assertTrue(remove_produto_image_at('short', 0))
        produto.refresh_from_db()
        self.assertTrue(produto.galeria_no_banco)
        self.assertEqual(produto.imagens.count(), 0)
        self.assertEqual(list_produto_images('short'), [])
        self.assertTrue((self.static / 'short' / 'imagem1.svg').is_file())

    def test_save_writes_uploads_in_selection_order(self):
        self._produto('novo')
        first = b'\x89PNG\r\n\x1a\n' + b'aaa'
        second = b'\x89PNG\r\n\x1a\n' + b'bbb'
        saved = save_produto_images('novo', [
            _png('b.png', b'aaa'),
            _png('a.png', b'bbb'),
        ])
        self.assertEqual(saved, ['01.png', '02.png'])
        rows = list(ProdutoImagem.objects.filter(produto__slug='novo').order_by('ordem'))
        self.assertEqual(bytes(rows[0].conteudo), first)
        self.assertEqual(bytes(rows[1].conteudo), second)
        urls = list_produto_images('novo')
        self.assertEqual(len(urls), 2)
        self.assertIn('01.png', urls[0])
        self.assertIn('02.png', urls[1])


class ProdutoEditPageTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.tmp.name)
        self.override.enable()
        self.addCleanup(self.override.disable)

        user = get_user_model().objects.create_superuser(
            username='staff',
            email='staff@example.com',
            password='password12345',
        )
        self.client.force_login(user)
        self.produto = Produto.objects.create(
            nome='Camisa',
            descricao='Algodão',
            preco='80.00',
            ativo=True,
            slug='camisa',
        )

    def test_edit_shows_storefront_images_in_order(self):
        response = self.client.get(
            reverse('produtos:admin_editar', args=[self.produto.id]),
        )
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertLess(content.index('imagem1.svg'), content.index('imagem2.svg'))
        self.assertLess(content.index('imagem2.svg'), content.index('imagem3.svg'))
        self.assertContains(response, 'Imagem 1')
        self.assertContains(response, 'Imagem 3')
        self.assertContains(response, 'Substituir')
        self.assertContains(response, 'Remover')
        self.assertContains(response, 'Adicionar imagem')
        self.assertContains(response, 'name="slot"')
        self.assertContains(response, 'value="0"')

    def test_replace_first_image_shows_on_home(self):
        response = self.client.post(
            reverse('produtos:admin_editar', args=[self.produto.id]),
            {
                'nome': 'Camisa',
                'descricao': 'Algodão',
                'preco': '80.00',
                'ativo': 'on',
                'slug': 'camisa',
                'substituir_0': _png('nova.png'),
            },
        )
        self.assertEqual(response.status_code, 302)
        home = self.client.get(reverse('produtos:home'))
        body = home.content.decode()
        self.assertIn('/media/produtos/camisa/01.png', body)
        self.assertIn('/media/produtos/camisa/02.svg', body)
        self.assertIn('/media/produtos/camisa/03.svg', body)
        self.assertLess(body.index('01.png'), body.index('02.svg'))
        self.assertLess(body.index('02.svg'), body.index('03.svg'))

    def test_home_lists_static_svg_until_upload(self):
        home = self.client.get(reverse('produtos:home'))
        body = home.content.decode()
        self.assertIn('/static/images/produtos/camisa/imagem1.svg', body)
        self.assertNotIn('/media/produtos/camisa/', body)


class ProdutoCreateImageTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser(
            username='staff',
            email='staff@example.com',
            password='password12345',
        )
        self.client.force_login(user)

    def test_create_page_can_add_another_image(self):
        response = self.client.get(reverse('produtos:admin_criar'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Adicionar outra imagem')
        self.assertContains(response, 'id="imagem-slots"')
        self.assertContains(response, 'no máximo 8 imagens')
        self.assertContains(response, 'Até 1')
        html = response.content.decode()
        self.assertNotIn(' multiple', html)
        self.assertNotIn('multiple=', html)

    def test_create_saves_two_images_in_order(self):
        first = b'\x89PNG\r\n\x1a\n' + b'aaa'
        second = b'\x89PNG\r\n\x1a\n' + b'bbb'
        response = self.client.post(
            reverse('produtos:admin_criar'),
            {
                'nome': 'Bone novo',
                'descricao': 'Aba',
                'preco': '40.00',
                'ativo': 'on',
                'slug': 'bone-novo',
                'imagens': [_png('um.png', b'aaa'), _png('dois.png', b'bbb')],
            },
        )
        self.assertEqual(response.status_code, 302)
        produto = Produto.objects.get(slug='bone-novo')
        self.assertTrue(produto.galeria_no_banco)
        rows = list(produto.imagens.order_by('ordem'))
        self.assertEqual([row.ordem for row in rows], [0, 1])
        self.assertEqual(bytes(rows[0].conteudo), first)
        self.assertEqual(bytes(rows[1].conteudo), second)
        self.assertEqual([row.sufixo for row in rows], ['.png', '.png'])

    @override_settings(DEBUG=False, SECURE_SSL_REDIRECT=False)
    def test_serve_image_when_debug_off(self):
        produto = Produto.objects.create(
            nome='Servida',
            descricao='',
            preco='10.00',
            slug='servida',
            galeria_no_banco=True,
        )
        ProdutoImagem.objects.create(
            produto=produto,
            ordem=0,
            sufixo='.png',
            conteudo=PNG_BYTES,
        )
        response = self.client.get(reverse('produtos:imagem', args=['servida', '01.png']))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, PNG_BYTES)
        self.assertEqual(response['Content-Type'], 'image/png')
        missing = self.client.get(reverse('produtos:imagem', args=['servida', '02.png']))
        self.assertEqual(missing.status_code, 404)
        wrong = self.client.get(reverse('produtos:imagem', args=['servida', '01.svg']))
        self.assertEqual(wrong.status_code, 404)


class ProdutoImageFormTests(TestCase):
    def _form(self, files):
        return ProdutoAdminForm(
            data={'nome': 'Peca', 'descricao': '', 'preco': '10.00', 'slug': 'peca'},
            files={'imagens': files},
        )

    def test_rejects_image_over_one_megabyte(self):
        too_big = SimpleUploadedFile(
            'grande.png',
            ONE_MB + b'0',
            content_type='image/png',
        )
        form = self._form([too_big])
        self.assertFalse(form.is_valid())
        self.assertIn('1 MB', form.errors['imagens'][0])

    def test_rejects_total_over_four_megabytes(self):
        files = [
            SimpleUploadedFile(f'f{i}.png', ONE_MB, content_type='image/png')
            for i in range(5)
        ]
        form = self._form(files)
        self.assertFalse(form.is_valid())
        self.assertIn('4 MB', form.errors['imagens'][0])

    def test_rejects_more_than_eight_images(self):
        files = [_png(f'f{i}.png') for i in range(9)]
        form = self._form(files)
        self.assertFalse(form.is_valid())
        self.assertIn('8', form.errors['imagens'][0])
