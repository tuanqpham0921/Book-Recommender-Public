import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import tailwindcss from '@tailwindcss/vite';

// https://vitejs.dev/config/
export default defineConfig({
  server: {
    port: 3000,
    historyApiFallback: true, // For SPA routing in development
  },
  preview: {
    port: 3000,
  },
  build: {
    // Ensure proper routing for production builds
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor libraries (React ecosystem)
          vendor: ['react', 'react-dom'],
          // Router
          router: ['react-router-dom'],
          // Large libraries
          mermaid: ['mermaid'],
          // UI libraries
          ui: ['lucide-react', 'react-spinners', 'use-immer'],
          // Markdown
          markdown: ['react-markdown', 'eventsource-parser'],
        },
      },
    },
    // Increase warning limit temporarily
    chunkSizeWarningLimit: 1000,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  plugins: [react(), tailwindcss()],
})
