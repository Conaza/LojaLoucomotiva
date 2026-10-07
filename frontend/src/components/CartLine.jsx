import { motion } from 'framer-motion'
import { formatBRL, labelTamanho } from '../format'
import { useCart } from '../cart-context'
import QtyControl from './QtyControl'

export default function CartLine({ line, placeholder, onError }) {
  const { update, remove, pending } = useCart()

  async function changeQty(quantidade) {
    onError?.('')
    try {
      await update({
        produto_id: line.produto_id,
        tamanho: line.tamanho,
        quantidade,
      })
    } catch (error) {
      onError?.(error.message)
    }
  }

  async function onRemove() {
    onError?.('')
    try {
      await remove(line)
    } catch (error) {
      onError?.(error.message)
    }
  }

  return (
    <motion.article
      className="cart-line"
      layout
      initial={{ opacity: 0, x: 28 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 36 }}
      transition={{ duration: 0.28 }}
    >
      <img
        className="cart-thumb"
        src={line.imagem || placeholder}
        alt={line.nome}
      />
      <div>
        <strong>{line.nome}</strong>
        <div className="small text-secondary">
          {labelTamanho(line.tamanho)}
          {' · '}
          R$ {formatBRL(line.preco_unitario)} / un.
        </div>
      </div>
      <div className="cart-line-actions">
        <QtyControl
          value={line.quantidade}
          disabled={pending}
          onChange={changeQty}
        />
        <button
          type="button"
          className="btn btn-sm btn-outline-danger"
          disabled={pending}
          onClick={onRemove}
        >
          Remover
        </button>
        <div className="cart-line-subtotal">R$ {formatBRL(line.subtotal)}</div>
      </div>
    </motion.article>
  )
}
