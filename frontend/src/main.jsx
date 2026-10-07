import { createRoot } from 'react-dom/client'
import { CartProvider } from './cart-context'
import { EMPTY_CART, readJsonScript } from './format'
import CartDrawer from './components/CartDrawer'
import { Vitrine } from './components/Vitrine'

const rootEl = document.getElementById('loja-root')

if (rootEl) {
  const checkoutUrl = rootEl.dataset.checkoutUrl || '/finalizar-pedido/'
  const placeholder = rootEl.dataset.placeholder || '/static/images/produtos/placeholder.svg'
  const carrinho = readJsonScript('carrinho-data', EMPTY_CART)
  const catalogo = readJsonScript('catalogo-data', [])

  createRoot(rootEl).render(
    <CartProvider initial={carrinho} startOpen={rootEl.dataset.openCart === '1'}>
      <Vitrine catalogo={catalogo} placeholder={placeholder} />
      <CartDrawer checkoutUrl={checkoutUrl} placeholder={placeholder} />
    </CartProvider>,
  )
}
