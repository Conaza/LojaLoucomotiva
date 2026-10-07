import { rmSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const root = dirname(fileURLToPath(import.meta.url))
const outDir = resolve(root, '../static/frontend')

function dropIndexHtml() {
  return {
    name: 'drop-index-html',
    apply: 'build',
    closeBundle() {
      rmSync(resolve(outDir, 'index.html'), { force: true })
    },
  }
}

export default defineConfig({
  plugins: [react(), dropIndexHtml()],
  base: '/static/frontend/',
  build: {
    outDir,
    emptyOutDir: true,
    sourcemap: false,
    modulePreload: false,
    rollupOptions: {
      output: {
        entryFileNames: 'loja.js',
        chunkFileNames: 'loja-[name].js',
        assetFileNames: 'loja.[ext]',
      },
    },
  },
})
