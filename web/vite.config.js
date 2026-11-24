import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// 개발 중에는 /api 요청(WebSocket 포함)을 FastAPI 서버(8000)로 넘긴다.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // three.js 묶음(3D 화면)은 따로 나뉘어 필요할 때만 받으므로 경고 기준을 그만큼 올린다
  build: { chunkSizeWarningLimit: 1100 },
  server: {
    proxy: { "/api": { target: "http://127.0.0.1:8000", ws: true } },
  },
});
