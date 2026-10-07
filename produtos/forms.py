"""Forms for staff product management."""

from django import forms
from django.conf import settings
from django.utils.text import slugify

from .models import Produto, Tamanho


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """FileField that accepts one or more uploads (widget with multiple=True)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if not data and data is not False:
            return [] if not self.required else single_clean(data, initial)
        if isinstance(data, (list, tuple)):
            if not data:
                return [] if not self.required else single_clean(None, initial)
            return [single_clean(item, initial) for item in data]
        return [single_clean(data, initial)]


def _png_widget():
    return forms.ClearableFileInput(attrs={
        'class': 'form-control',
        'accept': 'image/png',
    })


class ProdutoAdminForm(forms.ModelForm):
    tamanhos = forms.MultipleChoiceField(
        label='Tamanhos disponíveis',
        choices=Tamanho.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
    )
    imagens = MultipleFileField(
        label='Imagens',
        required=False,
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/png',
        }),
    )

    class Meta:
        model = Produto
        fields = ['nome', 'descricao', 'preco', 'ativo', 'slug']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'preco': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'gerado automaticamente se vazio',
            }),
        }

    def __init__(self, *args, slug_readonly=False, gallery_count=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.gallery_count = gallery_count
        self.fields['slug'].required = False
        if slug_readonly:
            self.fields['slug'].widget.attrs['readonly'] = True
            self.fields['slug'].help_text = 'O slug não pode ser alterado após a criação.'
        editing = bool(self.instance and self.instance.pk)
        if editing:
            self.fields.pop('imagens', None)
            for index in range(gallery_count):
                self.fields[f'substituir_{index}'] = forms.FileField(
                    label='Substituir',
                    required=False,
                    widget=_png_widget(),
                )
            self.fields['nova_imagem'] = forms.FileField(
                label='Adicionar imagem',
                required=False,
                widget=_png_widget(),
            )
            self.fields['tamanhos'].initial = [
                t.tamanho for t in self.instance.tamanhos.filter(disponivel=True)
            ]

    def clean_slug(self):
        slug = (self.cleaned_data.get('slug') or '').strip().lower()
        nome = self.cleaned_data.get('nome') or ''
        if not slug:
            slug = slugify(nome)
        if not slug:
            raise forms.ValidationError('Informe um slug ou um nome válido.')
        qs = Produto.objects.filter(slug=slug)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Já existe um produto com este slug.')
        return slug

    def _clean_png(self, uploaded):
        if not uploaded:
            return None
        name = (getattr(uploaded, 'name', '') or '').lower()
        if not name.endswith('.png'):
            raise forms.ValidationError('Apenas arquivos PNG são aceitos.')
        size = getattr(uploaded, 'size', None)
        max_bytes = getattr(settings, 'MAX_PRODUTO_IMAGE_BYTES', 5 * 1024 * 1024)
        if size is not None and size > max_bytes:
            raise forms.ValidationError('Cada imagem deve ter no máximo 5 MB.')
        return uploaded

    def clean_imagens(self):
        files = self.cleaned_data.get('imagens') or []
        valid = []
        for uploaded in files:
            if not uploaded:
                continue
            valid.append(self._clean_png(uploaded))
        return valid

    def clean_nova_imagem(self):
        return self._clean_png(self.cleaned_data.get('nova_imagem'))

    def clean(self):
        cleaned = super().clean()
        for index in range(self.gallery_count):
            key = f'substituir_{index}'
            if key not in self.fields:
                continue
            try:
                cleaned[key] = self._clean_png(cleaned.get(key))
            except forms.ValidationError as exc:
                self.add_error(key, exc)
        return cleaned
