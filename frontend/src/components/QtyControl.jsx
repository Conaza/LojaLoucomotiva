export default function QtyControl({ value, onChange, disabled, min = 1, max = 20 }) {
  return (
    <div className="qty-control">
      <button
        type="button"
        aria-label="Diminuir"
        disabled={disabled || value <= min}
        onClick={() => onChange(value - 1)}
      >
        −
      </button>
      <span className="qty-value" aria-live="polite">{value}</span>
      <button
        type="button"
        aria-label="Aumentar"
        disabled={disabled || value >= max}
        onClick={() => onChange(value + 1)}
      >
        +
      </button>
    </div>
  )
}
