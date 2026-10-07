import { useState } from 'react'

export default function Carousel({ imagens, alt, placeholder }) {
  const fotos = imagens?.length ? imagens : [placeholder]
  const [index, setIndex] = useState(0)
  const atual = Math.min(index, fotos.length - 1)

  function step(delta, event) {
    event.stopPropagation()
    setIndex((current) => (current + delta + fotos.length) % fotos.length)
  }

  return (
    <div className="product-carousel" data-carousel>
      {fotos.map((src, i) => (
        <img
          key={`${src}-${i}`}
          src={src}
          alt={alt}
          className={i === atual ? 'is-active' : undefined}
        />
      ))}
      {fotos.length > 1 && (
        <div className="carousel-nav">
          <button type="button" data-carousel-prev aria-label="Anterior" onClick={(event) => step(-1, event)}>
            &lt;
          </button>
          <span className="carousel-counter">
            <span data-carousel-current>{atual + 1}</span>
            {` / ${fotos.length}`}
          </span>
          <button type="button" data-carousel-next aria-label="Próxima" onClick={(event) => step(1, event)}>
            &gt;
          </button>
        </div>
      )}
    </div>
  )
}
