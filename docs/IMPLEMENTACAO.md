# Implementação

Passo a passo para instalar a Loucomotiva, configurar o ambiente e publicar a loja. A descrição do que o site faz está no [README](../README.md). O pagamento pela InfinitePay está em [INTEGRACAO_INFINITEPAY.md](INTEGRACAO_INFINITEPAY.md).

## Tecnologias

- Python 3.x
- Django
- MySQL (PyMySQL)
- HTML / CSS / JavaScript
- Bootstrap 5 (CDN)
- Gunicorn + WhiteNoise (produção)

O driver é o PyMySQL, em Python puro. O build não precisa das bibliotecas de desenvolvimento do MySQL (`libmysqlclient` / `pkg-config`), o que permite publicar em ambientes como a Vercel.

## Estrutura

```text
config/       # settings, urls, wsgi
produtos/     # catálogo, tamanhos, imagens
carrinho/     # sessão
pedidos/      # checkout, confirmação, admin-pedidos
templates/
static/
docs/
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
| `ALLOWED_HOSTS` | Hosts separados por vírgula. Em produção, inclua o domínio público do site |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | MySQL |
| `DB_SSL` | `True` para MySQL remoto com TLS (ex.: Aiven) |
| `INFINITEPAY_*` / `SITE_URL` | InfiniteTag, token do webhook e URL pública do site — veja [INTEGRACAO_INFINITEPAY.md](INTEGRACAO_INFINITEPAY.md) |

O arquivo `.env` não deve ir para o GitHub. Na Vercel (ou em outro provedor), cadastre as mesmas variáveis no painel do projeto.

## Imagens dos produtos

Fotos enviadas pelo painel ficam na tabela `ProdutoImagem` (MySQL), ligadas ao produto. A loja entrega cada arquivo em `/media/produtos/<slug>/01.png`. Isso vale na Vercel, onde o disco da função não guarda arquivo.

Enquanto o produto não tiver imagens no banco, a vitrine usa os arquivos estáticos que já estão no repositório:

```text
static/images/produtos/<slug>/imagem1.svg
```

O campo `slug` identifica a galeria. O painel aceita PNG, até 1 MB por arquivo, no máximo 8 imagens e 4 MB somados no mesmo envio. Na criação, o botão «Adicionar outra imagem» inclui mais um campo; a ordem dos campos é a ordem do carrossel.

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
| `/admin-pedidos/excel/` | Exportação dos pedidos em Excel (staff) |
| `/admin/` | Django Admin |

## Produção / deploy

1. `DEBUG=False`, `SECRET_KEY` forte, `ALLOWED_HOSTS` com o domínio público
2. `DB_SSL=True` se o MySQL for remoto
3. `python manage.py collectstatic`
4. Subir com Gunicorn (`Procfile` incluso) + HTTPS no provedor
5. Com `DEBUG=False`, cookies Secure, HSTS e redirect SSL são ativados automaticamente

### MySQL remoto (ex.: Aiven)

Use host, porta, usuário e senha do provedor no `.env` e `DB_SSL=True`. A aplicação não depende de um provedor específico.

### Vercel

O `requirements.txt` usa PyMySQL de propósito: o `mysqlclient` não compila na imagem de build da Vercel. Na Vercel o app aceita qualquer host `*.vercel.app` (o Django usa o curinga `.vercel.app`). Defina `SITE_URL` com a URL HTTPS pública.

## Comandos úteis

```bash
python manage.py seed_produtos
python manage.py collectstatic
python manage.py createsuperuser
```
