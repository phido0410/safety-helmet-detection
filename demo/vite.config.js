// HelmetCheck (demo của ĐATN). npm run dev: HTTPS trong mạng nội bộ để mở trên iPhone (camera, WebGPU và WASM đa luồng cần HTTPS
// và crossOriginIsolated). Chứng chỉ tự ký tạo một lần bằng openssl vào .cert/ (không commit), tạo lại khi IP máy đổi; lần đầu
// Safari báo kết nối không riêng tư: Hiển thị chi tiết → truy cập trang web này. Vercel đặt cùng header COOP/COEP (vercel.json).
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync } from "node:fs";
import { networkInterfaces } from "node:os";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const PORT = 8443;
// header COOP/COEP lấy từ vercel.json để bản chạy thử và bản trên Vercel không lệch nhau
const ISOLATION = Object.fromEntries(JSON.parse(readFileSync("vercel.json", "utf8")).headers[0].headers.map((h) => [h.key, h.value]));

// mũ của màn giới thiệu và của biểu tượng app (scripts/make_demo_icons.py) dùng chung một file; nhúng vào trang để hiện ngay, không chờ tải
const inlineHat = { name: "inline-hat", transformIndexHtml: (html) => html.replace("<!--hat-->", readFileSync("public/icons/hat.svg", "utf8")) };

// CSS của app nằm sau màn giới thiệu nên không được chặn lần vẽ đầu của màn đó
const lazyCss = { name: "lazy-css", transformIndexHtml: { order: "post", handler: (html) => html.replace(/<link rel="stylesheet"( crossorigin)? href="([^"]+)">/,
  (_, cors = "", href) => `<link rel="stylesheet"${cors} href="${href}" media="print" onload="this.media='all'">`) } };

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
    plugins: [react(), inlineHat, lazyCss],
    server,
    preview: server,
    build: { rolldownOptions: { input: { main: "index.html", bench: "bench.html" } } },
  };
});
