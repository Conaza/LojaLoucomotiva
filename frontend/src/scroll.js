export function lockScroll() {
  const count = Number(document.body.dataset.scrollLock || '0')
  if (count === 0) {
    document.body.dataset.prevOverflow = document.body.style.overflow
  }
  document.body.dataset.scrollLock = String(count + 1)
  document.body.style.overflow = 'hidden'
}

export function unlockScroll() {
  const count = Number(document.body.dataset.scrollLock || '1') - 1
  if (count <= 0) {
    document.body.style.overflow = document.body.dataset.prevOverflow || ''
    delete document.body.dataset.scrollLock
    delete document.body.dataset.prevOverflow
    return
  }
  document.body.dataset.scrollLock = String(count)
}
