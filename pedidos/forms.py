from django import forms

from .models import FormaPagamento


class FinalizarPedidoForm(forms.Form):
    nome = forms.CharField(
        label='Nome',
        max_length=120,
        strip=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autocomplete': 'name',
            'required': True,
        }),
    )
    contato = forms.RegexField(
        label='Contato (telefone/WhatsApp)',
        max_length=40,
        regex=r'^[\d\s\+\(\)\-]+$',
        error_messages={
            'invalid': 'Informe um telefone válido.',
        },
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autocomplete': 'tel',
            'placeholder': '31999999999',
            'required': True,
        }),
    )
    forma_pagamento = forms.ChoiceField(
        label='Forma de pagamento',
        choices=FormaPagamento.choices,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        required=True,
    )
