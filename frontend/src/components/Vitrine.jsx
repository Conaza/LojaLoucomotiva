import { useCallback, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { formatBRL } from '../format'
import Carousel from './Carousel'
import ProductModal from './ProductModal'

export default function ProductCard({ produto, placeholder, onOpen, index }) {
  return (
    <motion.article
      className="product-tile"
      initial={{ opacity: 0, y: 28 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.08, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -6 }}
    >
      <Carousel imagens={produto.imagens} alt={produto.nome} placeholder={placeholder} />
      <div className="product-body">
        <h2>{produto.nome}</h2>
        <div className="price">R$ {formatBRL(produto.preco)}</div>
        <button type="button" className="btn btn-accent w-100" onClick={() => onOpen(produto)}>
          Comprar
        </button>
      </div>
    </motion.article>
  )
}

export function Vitrine({ catalogo, placeholder }) {
  const [aberto, setAberto] = useState(null)
  const close = useCallback(() => setAberto(null), [])

  if (!catalogo.length) {
    return <p>Nenhum produto disponível no momento.</p>
  }

  return (
    <>
      <section className="product-grid">
        {catalogo.map((produto, index) => (
          <ProductCard
            key={produto.id}
            produto={produto}
            placeholder={placeholder}
            index={index}
            onOpen={setAberto}
          />
        ))}
      </section>
      <AnimatePresence>
        {aberto ? (
          <ProductModal
            key={aberto.id}
            produto={aberto}
            placeholder={placeholder}
            onClose={close}
          />
        ) : null}
      </AnimatePresence>
    </>
  )
}
