import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { adicionarItem, atualizarItem, removerItem } from './api'
const CartContext = createContext(null)

function syncBadge(quantidade) {
  const link = document.getElementById('carrinho-link')
  if (!link) return
  const qtd = Number(quantidade) || 0
  link.textContent = qtd > 0 ? `Carrinho (${qtd})` : 'Carrinho'
}

export function CartProvider({ initial, startOpen = false, children }) {
  const [cart, setCart] = useState(initial)
  const [pending, setPending] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(startOpen)

  useEffect(() => {
    syncBadge(cart.quantidade_total)
  }, [cart.quantidade_total])

  const openDrawer = useCallback(() => setDrawerOpen(true), [])

  useEffect(() => {
    const link = document.getElementById('carrinho-link')
    if (!link) return undefined
    function onClick(event) {
      event.preventDefault()
      openDrawer()
    }
    link.addEventListener('click', onClick)
    return () => link.removeEventListener('click', onClick)
  }, [openDrawer])

  const apply = useCallback((next) => {
    setCart(next)
    syncBadge(next.quantidade_total)
  }, [])

  const closeDrawer = useCallback(() => setDrawerOpen(false), [])

  const add = useCallback(async (payload) => {
    setPending(true)
    try {
      const next = await adicionarItem(payload)
      apply(next)
      setDrawerOpen(true)
      return next
    } finally {
      setPending(false)
    }
  }, [apply])

  const update = useCallback(async (payload) => {
    setPending(true)
    try {
      const next = await atualizarItem(payload)
      apply(next)
      return next
    } finally {
      setPending(false)
    }
  }, [apply])

  const remove = useCallback(async (line) => {
    setPending(true)
    try {
      const next = await removerItem({
        produto_id: line.produto_id,
        tamanho: line.tamanho,
      })
      apply(next)
      return next
    } finally {
      setPending(false)
    }
  }, [apply])

  return (
    <CartContext.Provider value={{
      cart,
      pending,
      drawerOpen,
      openDrawer,
      closeDrawer,
      add,
      update,
      remove,
    }}
    >
      {children}
    </CartContext.Provider>
  )
}

export function useCart() {
  const value = useContext(CartContext)
  if (!value) {
    throw new Error('useCart fora do Carrinho')
  }
  return value
}
