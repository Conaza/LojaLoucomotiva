"""Gallery slot behavior for product images."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from produtos.images import (
    list_produto_gallery,
    list_produto_images,
    remove_produto_image_at,
    replace_produto_image,
    save_produto_images,
)
from produtos.models import Produto

PNG_BYTES = b'\x89PNG\r\n\x1a\n' + b'0' * 16
_IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg'}


def _png(name='foto.png'):
    return SimpleUploadedFile(name, PNG_BYTES, content_type='image/png')


def _image_names(folder: Path) -> list[str]:
    return sorted(
        p.name for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in _IMAGE_SUFFIXES
    )


class ProdutoGalleryTests(SimpleTestCase):
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
        self.assertTrue(replace_produto_image('camisa', 0, _png('nova.png')))
        self.assertEqual(_image_names(self.media / 'camisa'), ['01.png', '02.svg', '03.svg'])
        self.assertTrue((self.static / 'camisa' / 'imagem1.svg').is_file())
        self.assertIn(b'imagem2.svg', (self.media / 'camisa' / '02.svg').read_bytes())
        urls = list_produto_images('camisa')
        self.assertEqual(len(urls), 3)
        self.assertIn('/media/produtos/camisa/01.png', urls[0])
        self.assertIn('/media/produtos/camisa/02.svg', urls[1])
        self.assertIn('/media/produtos/camisa/03.svg', urls[2])

    def test_remove_renumbers_following_images(self):
        self._static('bone', ['imagem1.svg', 'imagem2.svg'])
        self.assertTrue(remove_produto_image_at('bone', 0))
        self.assertEqual(_image_names(self.media / 'bone'), ['01.svg'])
        self.assertIn(b'imagem2.svg', (self.media / 'bone' / '01.svg').read_bytes())
        urls = list_produto_images('bone')
        self.assertEqual(len(urls), 1)
        self.assertIn('01.svg', urls[0])

    def test_remove_all_does_not_restore_static(self):
        self._static('short', ['imagem1.svg'])
        self.assertTrue(remove_produto_image_at('short', 0))
        self.assertEqual(list_produto_images('short'), [])

    def test_save_writes_uploads_in_selection_order(self):
        saved = save_produto_images('novo', [_png('b.png'), _png('a.png')])
        self.assertEqual(saved, ['01.png', '02.png'])
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
