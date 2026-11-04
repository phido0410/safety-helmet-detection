// Service worker của HelmetCheck: lần mở đầu lưu lại mọi file cùng nguồn (mô hình, onnxruntime-web, JS, CSS, font) để lần sau
// mở được khi không có mạng. Trang chính và config.json lấy mạng trước (để nhận bản mới; config.json đổi định dạng thì bản cũ đã lưu
// làm app báo lỗi), lỗi mạng thì dùng bản đã lưu.
const CACHE = "helmetcheck-v2";  // đổi tên khi giao diện đổi để bỏ bản cũ đã lưu

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil((async () => {
  for (const key of await caches.keys()) if (key !== CACHE) await caches.delete(key);
  await self.clients.claim();
})()));

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    if (req.mode === "navigate" || new URL(req.url).pathname.endsWith("/config.json")) {
      try {
        const res = await fetch(req);
        cache.put(req, res.clone());
        return res;
      } catch {
        return (await cache.match(req)) ?? Response.error();
      }
    }
    const hit = await cache.match(req);
    if (hit) return hit;
    const res = await fetch(req);
    if (res.ok) cache.put(req, res.clone());
    return res;
  })());
});
