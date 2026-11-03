// HelmetCheck (demo của ĐATN). npm run dev: HTTPS trong mạng nội bộ để mở trên iPhone (camera, WebGPU và WASM đa luồng cần HTTPS
// và crossOriginIsolated). Chứng chỉ tự ký tạo một lần bằng openssl vào .cert/ (không commit), tạo lại khi IP máy đổi; lần đầu
// Safari báo kết nối không riêng tư: Hiển thị chi tiết → truy cập trang web này. Vercel đặt cùng header COOP/COEP (vercel.json).
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync } from "node:fs";
import { networkInterfaces } from "node:os";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const PORT = 8443;
const ISOLATION = { "Cross-Origin-Opener-Policy": "same-origin", "Cross-Origin-Embedder-Policy": "require-corp" };

const lanIp = () => Object.values(networkInterfaces()).flat().find((a) => a.family === "IPv4" && !a.internal)?.address ?? "127.0.0.1";

function devCert() {
  const ip = lanIp(), key = ".cert/key.pem", cert = ".cert/cert.pem";
  const valid = existsSync(cert) && execFileSync("openssl", ["x509", "-in", cert, "-noout", "-text"]).toString().includes(ip);
  if (!valid) {
    mkdirSync(".cert", { recursive: true });
    execFileSync("openssl", ["req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", key, "-out", cert, "-days", "30",
      "-subj", "/CN=HelmetCheck dev", "-addext", `subjectAltName=IP:${ip},DNS:localhost`], { stdio: "ignore" });
  }
  console.log(`  iPhone (cùng Wi-Fi): https://${ip}:${PORT}/`);
  return { key: readFileSync(key), cert: readFileSync(cert) };
}

export default defineConfig(({ command }) => {
  const server = command === "serve" ? { host: true, port: PORT, strictPort: true, https: devCert(), headers: ISOLATION } : {};
  return {
    plugins: [react()],
    server,
    preview: server,
    build: { rolldownOptions: { input: { main: "index.html", bench: "bench.html" } } },
  };
});
