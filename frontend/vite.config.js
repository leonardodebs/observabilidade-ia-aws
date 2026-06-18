import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Configuracao do Vite.
// As chamadas a /api/* sao encaminhadas ao proxy FastAPI (porta 8000),
// evitando CORS e mantendo a assinatura SigV4 no backend local.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
