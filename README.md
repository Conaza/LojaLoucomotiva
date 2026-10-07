# Loucomotiva — Loja Virtual

Loja virtual simples com Django + MySQL: catálogo com carrossel, modal de compra, carrinho em sessão, checkout com pagamento por Pix ou cartão no checkout da InfinitePay (veja [docs/INTEGRACAO_INFINITEPAY.md](docs/INTEGRACAO_INFINITEPAY.md)) e painel de pedidos para staff.

## Tecnologias

- Python 3.x
- Django
- MySQL (`mysqlclient`)
- HTML / CSS / JavaScript
- Bootstrap 5 (CDN)
- Gunicorn + WhiteNoise (produção)

## Estrutura

```text
config/       # settings, urls, wsgi
produtos/     # catálogo, tamanhos, imagens
carrinho/     # sessão
pedidos/      # checkout, confirmação, admin-pedidos
templates/
static/
```

## Instalação local

```bash
python -m venv venv
# Windows (PowerShell). Se aparecer "execução de scripts foi desabilitada",
# libere só para a sessão atual antes de ativar:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # ou cp .env.example .env
```

Edite o `.env` com `SECRET_KEY`, credenciais MySQL e `ALLOWED_HOSTS`.

Crie o banco MySQL (utf8mb4), por exemplo:

```sql
CREATE DATABASE loucomotiva CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

```bash
python manage.py migrate
python manage.py seed_produtos
python manage.py createsuperuser
python manage.py runserver
```

Abra http://127.0.0.1:8000/

## Variáveis de ambiente (`.env`)

| Variável | Descrição |
|----------|-----------|
| `SECRET_KEY` | Chave secreta Django (obrigatória; não use `change-me` em produção) |
| `DEBUG` | `True` local / `False` produção |
| `ALLOWED_HOSTS` | Hosts separados por vírgula |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | MySQL |
| `DB_SSL` | `True` para MySQL remoto com TLS (ex.: Aiven) |
| `INFINITEPAY_*` / `SITE_URL` | InfiniteTag, token do webhook e URL pública do site — veja [docs/INTEGRACAO_INFINITEPAY.md](docs/INTEGRACAO_INFINITEPAY.md) |

O arquivo `.env` **não** deve ir para o GitHub.

## Imagens dos produtos

Organize em:

```text
static/images/produtos/<slug>/imagem1.jpg
```

O campo `slug` do produto aponta para a pasta. Substitua os placeholders SVG por fotos reais mantendo o mesmo `slug`.

## URLs principais

| URL | Função |
|-----|--------|
| `/` | Catálogo |
| `/carrinho/` | Carrinho |
| `/finalizar-pedido/` | Checkout |
| `/pedido/sucesso/<id>/` | Confirmação (somente o pedido da sessão) |
| `/pedido/<id>/pagamento/retorno/` | Retorno do checkout InfinitePay (confirma o pagamento) |
| `/pagamentos/infinitepay/webhook/` | Webhook da InfinitePay |
| `/admin-pedidos/` | Lista de pedidos (staff) |
| `/admin/` | Django Admin |

## Produção / deploy

1. `DEBUG=False`, `SECRET_KEY` forte, `ALLOWED_HOSTS` corretos
2. `DB_SSL=True` se o MySQL for remoto
3. `python manage.py collectstatic`
4. Subir com Gunicorn (`Procfile` incluso) + HTTPS no provedor
5. Com `DEBUG=False`, cookies Secure, HSTS e redirect SSL são ativados automaticamente

### MySQL remoto (ex.: Aiven)

Use host/porta/usuário/senha do provedor no `.env` e `DB_SSL=True`. A aplicação não depende de um provedor específico.

## Segurança (resumo)

- Credenciais só via `.env`
- CSRF em todos os POSTs do carrinho/checkout
- Preço sempre recalculado no backend
- Página de sucesso anti-IDOR (sessão)
- `/admin-pedidos/` exige `is_staff`
- Slug de imagens sanitizado (anti path traversal)

## Comandos úteis

```bash
python manage.py seed_produtos
python manage.py collectstatic
python manage.py createsuperuser
```
