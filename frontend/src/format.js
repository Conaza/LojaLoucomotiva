export const EMPTY_CART = {
  lines: [],
  quantidade_total: 0,
  valor_total: '0.00',
  vazio: true,
}

export function formatBRL(value) {
  const number = Number(value)
  if (Number.isNaN(number)) return '0,00'
  return number.toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

export function labelTamanho(tamanho) {
  return tamanho === 'Unico' ? 'Único' : tamanho
}

export function lineKey(line) {
  return `${line.produto_id}:${line.tamanho}`
}

export function readJsonScript(id, fallback) {
  const el = document.getElementById(id)
  if (!el) return fallback
  try {
    return JSON.parse(el.textContent)
  } catch {
    return fallback
  }
}
