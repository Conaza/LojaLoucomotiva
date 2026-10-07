const NETWORK_ERROR = 'Não foi possível atualizar o carrinho.'

function csrfToken() {
  return document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
}

async function readBody(response) {
  const text = await response.text()
  if (!text) return {}
  try {
    return JSON.parse(text)
  } catch {
    return {}
  }
}

async function postJson(url, payload) {
  let response
  try {
    response = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken(),
      },
      body: JSON.stringify(payload),
    })
  } catch {
    throw new Error(NETWORK_ERROR)
  }
  const data = await readBody(response)
  if (!response.ok) {
    throw new Error(data.error || NETWORK_ERROR)
  }
  return data
}

export function adicionarItem(payload) {
  return postJson('/carrinho/api/adicionar/', {
    produto_id: payload.produto_id,
    tamanho: payload.tamanho,
    quantidade: payload.quantidade,
  })
}

export function atualizarItem(payload) {
  return postJson('/carrinho/api/atualizar/', {
    produto_id: payload.produto_id,
    tamanho: payload.tamanho,
    quantidade: payload.quantidade,
  })
}

export function removerItem(payload) {
  return postJson('/carrinho/api/remover/', {
    produto_id: payload.produto_id,
    tamanho: payload.tamanho,
  })
}
