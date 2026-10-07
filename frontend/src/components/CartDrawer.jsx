import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { formatBRL } from '../format'
import { lockScroll, unlockScroll } from '../scroll'
import { useCart } from '../cart-context'
import CartLine from './CartLine'

const drawerEase = { type: 'spring', stiffness: 380, damping: 36 }

export default function CartDrawer({ checkoutUrl, placeholder }) {
  const { cart, drawerOpen, closeDrawer, pending } = useCart()
  const closeRef = useRef(null)
  const [error, setError] = useState('')
  const lines = cart.lines || []
  const vazio = cart.vazio || lines.length === 0

  useEffect(() => {
    if (!drawerOpen) return undefined
    setError('')
    lockScroll()
    closeRef.current?.focus()
    function onKey(event) {
      if (event.key === 'Escape') closeDrawer()
    }
    document.addEventListener('keydown', onKey)
    return () => {
      unlockScroll()
      document.removeEventListener('keydown', onKey)
    }
  }, [drawerOpen, closeDrawer])

  return (
    <AnimatePresence>
      {drawerOpen ? (
        <motion.div
          className="cart-drawer-root"
          key="cart-drawer"
          initial={{ opacity: 1 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 1 }}
          transition={{ duration: 0.45 }}
        >
          <motion.button
            type="button"
            className="cart-drawer-backdrop"
            aria-label="Fechar carrinho"
            onClick={closeDrawer}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.28 }}
          />
          <motion.aside
            className="cart-drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="cart-drawer-title"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={drawerEase}
          >
            <header className="cart-drawer-header">
              <h2 id="cart-drawer-title">Carrinho</h2>
              <button
                ref={closeRef}
                type="button"
                className="btn-close"
                aria-label="Fechar"
                onClick={closeDrawer}
              />
            </header>
            <div className="cart-drawer-body">
              {error ? <p className="text-danger" role="alert">{error}</p> : null}
              {vazio ? (
                <p className="text-secondary">Seu carrinho está vazio.</p>
              ) : (
                <AnimatePresence initial={false}>
                  {lines.map((line) => (
                    <CartLine
                      key={`${line.produto_id}:${line.tamanho}`}
                      line={line}
                      placeholder={placeholder}
                      onError={setError}
                    />
                  ))}
                </AnimatePresence>
              )}
            </div>
            <footer className="cart-drawer-footer">
              <p className="fs-5 fw-bold mb-3">TOTAL: R$ {formatBRL(cart.valor_total)}</p>
              <button
                type="button"
                className="btn btn-outline-ink"
                onClick={closeDrawer}
                disabled={pending}
              >
                Continuar comprando
              </button>
              {vazio ? null : (
                <a className="btn btn-accent" href={checkoutUrl}>
                  Finalizar pedido
                </a>
              )}
            </footer>
          </motion.aside>
        </motion.div>
      ) : null}
    </AnimatePresence>
  )
}
