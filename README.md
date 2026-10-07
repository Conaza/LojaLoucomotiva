# Loucomotiva — Loja Virtual

Loja de roupas em que o cliente escolhe o produto, monta o carrinho e paga com Pix ou cartão. A equipe acompanha os pedidos e mantém o catálogo pelo painel.

## Para quem compra

- **Catálogo.** A página inicial lista os produtos ativos, com carrossel de fotos, preço e descrição.
- **Compra.** Um modal pede o tamanho (PP, P, M, G, GG, XG ou único) e a quantidade. Só entram tamanhos marcados como disponíveis.
- **Carrinho.** Os itens ficam na sessão. Dá para alterar a quantidade, remover uma peça ou esvaziar o carrinho antes de fechar o pedido.
- **Checkout.** O cliente informa nome e telefone. O valor é calculado de novo no servidor, a partir do preço cadastrado e do que está no carrinho.
- **Pagamento.** Ao finalizar, a loja abre o checkout da InfinitePay. O cliente paga com Pix ou cartão de crédito nessa página e volta para a loja.
- **Confirmação.** A página de sucesso mostra se o pagamento já foi confirmado ou se ainda está aguardando. Ela só abre para o pedido da própria sessão.

O fluxo do pagamento, do webhook e do retorno está em [docs/INTEGRACAO_INFINITEPAY.md](docs/INTEGRACAO_INFINITEPAY.md).

## Para a equipe

- **Pedidos.** Quem tem acesso de staff vê a lista em `/admin-pedidos/`, com cliente, itens, total e status do pagamento (aguardando ou pago).
- **Planilha.** A mesma lista pode ser baixada em Excel.
- **Catálogo.** No painel dá para criar, editar e excluir produtos, escolher os tamanhos disponíveis e trocar as fotos da galeria.
- **Admin do Django.** Usuários e o restante dos dados também ficam em `/admin/`.

## O que a loja protege

- Credenciais ficam só no ambiente, fora do código.
- O preço e os itens do pedido são lidos de novo no servidor, a partir do carrinho e do cadastro.
- A confirmação de pagamento só vale depois que a InfinitePay confirma a transação e o valor.
- A página de sucesso abre só para o pedido guardado na sessão de quem comprou.
- O painel de pedidos e de produtos exige usuário staff.
- O nome da pasta de imagens é validado para não sair do diretório do produto.

Para subir o projeto localmente ou em produção, siga [docs/IMPLEMENTACAO.md](docs/IMPLEMENTACAO.md).
