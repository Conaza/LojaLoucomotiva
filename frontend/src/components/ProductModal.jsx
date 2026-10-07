import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { formatBRL, labelTamanho } from '../format'
import { lockScroll, unlockScroll } from '../scroll'
import { useCart } from '../cart-context'
import Carousel from './Carousel'
import QtyControl from './QtyControl'

export default function ProductModal({ produto, placeholder, onClose }) {
  const { add, pending } = useCart()
  const [tamanho, setTamanho] = useState('')
  const [quantidade, setQuantidade] = useState(1)
  const [error, setError] = useState('')

  useEffect(() => {
    lockScroll()
    function onKey(event) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => {
      unlockScroll()
      document.removeEventListener('keydown', onKey)
    }
  }, [onClose])

  async function onSubmit(event) {
    event.preventDefault()
    if (!tamanho) {
      setError('Selecione um tamanho.')
      return
    }
    setError('')
    try {
      await add({
        produto_id: produto.id,
        tamanho,
        quantidade,
      })
      onClose()
    } catch (err) {
      setError(err.message)
    }
  }

  const total = Number(produto.preco) * quantidade

  return (
    <motion.div
      className="store-modal-root"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
    >
      <button
        type="button"
        className="store-modal-backdrop"
        aria-label="Fechar"
        onClick={onClose}
      />
      <motion.div
        className="store-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="produto-modal-title"
        initial={{ opacity: 0, y: 28, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 16, scale: 0.98 }}
        transition={{ type: 'spring', stiffness: 420, damping: 34 }}
      >
        <header className="store-modal-header">
          <h2 id="produto-modal-title">{produto.nome}</h2>
          <button type="button" className="btn-close" aria-label="Fechar" onClick={onClose} />
        </header>
        <form onSubmit={onSubmit}>
          <div className="store-modal-body">
            <div className="store-modal-grid">
              <Carousel imagens={produto.imagens} alt={produto.nome} placeholder={placeholder} />
              <div>
                {produto.descricao ? <p className="text-secondary product-description">{produto.descricao}</p> : null}
                <p className="price">R$ {formatBRL(produto.preco)}</p>
                <div className="mb-3">
                  <p className="form-label" id="tamanho-label">Tamanho</p>
                  <div className="size-options" role="group" aria-labelledby="tamanho-label">
                    {produto.tamanhos.map((item) => (
                      <button
                        key={item}
                        type="button"
                        className={item === tamanho ? 'is-selected' : undefined}
                        aria-pressed={item === tamanho}
                        onClick={() => setTamanho(item)}
                      >
                        {labelTamanho(item)}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="mb-3">
                  <p className="form-label">Quantidade</p>
                  <QtyControl value={quantidade} onChange={setQuantidade} disabled={pending} />
                </div>
                <motion.p
                  className="fw-bold"
                  key={total}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  Total: R$ {formatBRL(total)}
                </motion.p>
                {error ? <p className="text-danger mt-2 mb-0" role="alert">{error}</p> : null}
              </div>
            </div>
          </div>
          <footer className="store-modal-footer">
            <button type="button" className="btn btn-outline-ink" onClick={onClose}>
              Fechar
            </button>
            <button type="submit" className="btn btn-accent" disabled={pending}>
              Adicionar ao carrinho
            </button>
          </footer>
        </form>
      </motion.div>
    </motion.div>
  )
}
