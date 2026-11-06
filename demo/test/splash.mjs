// Kiểm tra màn giới thiệu trên bản dựng thật (npm run build && npm run preview, hoặc bản đã đăng), Chrome không giao diện:
//   node demo/test/splash.mjs <url>
// 1 Lần đầu, mạng chậm: màn hiện trước khi JS tải xong, % tăng dần, thanh hiện, băng cắt chéo, rồi vào app.
// 2 Mở lại (đã có bộ nhớ đệm): không hiện thanh, không có nhịp băng, in thời gian tới lúc vào app.
// 3 Tải mô hình lỗi: dừng ở màn, nêu lý do, tiêu điểm vào Thử lại; Thử lại khi có mạng thì vào được; Vào app thì vẫn dùng được Lịch sử.
// 3b Mạng đứng giữa chừng: sau 20 s có lối thoát; dữ liệu chạy lại thì lối thoát tự ẩn và vào app bình thường; đứng hẳn thì Vào app được.
// 4 Giảm chuyển động: không có chuyển động, chỉ mờ dần.
// 5 Bố cục ở 4 cỡ màn: không tràn, không đè nhau.
import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";

const url = process.argv[2];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const timer = setTimeout(() => { console.log("hết giờ"); process.exit(2); }, 420000);
let failed = 0;
const check = (ok, msg) => { console.log(`${ok ? "đạt" : "SAI"}: ${msg}`); if (!ok) failed++; };
// ghi lại mỗi lần lớp của màn đổi (đổi rất nhanh, hỏi định kỳ sẽ sót), kèm độ mờ của thanh tiến độ lúc đó
const WATCH = `addEventListener("DOMContentLoaded", () => { const e = document.getElementById("splash"); window.__sp = { classes: [], removed: null, opacity: 0 };
  new MutationObserver(() => window.__sp.classes.push([Math.round(performance.now()), e.className])).observe(e, { attributes: true, attributeFilter: ["class"] });
  new MutationObserver(() => { if (!document.getElementById("splash") && window.__sp.removed === null) window.__sp.removed = Math.round(performance.now()); }).observe(document.body, { childList: true });
  setInterval(() => { const l = document.querySelector(".sp-load"); if (l && getComputedStyle(l).opacity > window.__sp.opacity) window.__sp.opacity = +getComputedStyle(l).opacity; }, 50); });`;

async function browser(port) {
  const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", ["--headless=new", `--remote-debugging-port=${port}`, "--ignore-certificate-errors", "--hide-scrollbars",
    `--user-data-dir=${mkdtempSync(tmpdir() + "/cdps")}`, "about:blank"], { stdio: "ignore" });
  let target;
  for (let i = 0; i < 50 && !target; i++) { await sleep(200); try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === "page"); } catch {} }
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => (ws.onopen = r));
  let id = 0;
  const pending = {}, errors = [];
  ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id) pending[d.id]?.(d); else if (d.method === "Runtime.exceptionThrown") errors.push(d.params.exceptionDetails.exception?.description ?? d.params.exceptionDetails.text); };
  const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
  const js = async (e) => (await send("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true })).result?.result?.value;
  const until = async (e, ms = 200000) => { for (let t = 0; t < ms; t += 100) { if (await js(e)) return true; await sleep(100); } throw new Error(`hết giờ: ${e}\n${errors.join("\n")}`); };
  await send("Runtime.enable"); await send("Page.enable"); await send("Network.enable");
  await send("Page.addScriptToEvaluateOnNewDocument", { source: WATCH });
  return { send, js, until, errors, close: () => { ws.close(); chrome.kill(); } };
}
const phone = (b, w = 414, h = 896) => b.send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: w < 800 });
const gone = "!document.getElementById('splash')";

// 1, 2: cùng một hồ sơ trình duyệt: lần đầu tải thật, lần sau có bộ nhớ đệm
{
  const b = await browser(9371);
  await phone(b);
  // service worker tự tải file thay trang nên giả lập mạng chậm không có tác dụng với nó: đi vòng qua ở lần này
  await b.send("Network.setBypassServiceWorker", { bypass: true });
  await b.send("Network.emulateNetworkConditions", { offline: false, latency: 40, downloadThroughput: 1_000_000, uploadThroughput: 1_000_000 });
  await b.send("Page.navigate", { url });
  await b.until("!!document.getElementById('sp-pct')", 30000);
  const pcts = [];
  while (!(await b.js(gone))) {
    const p = parseInt(await b.js("document.getElementById('sp-pct')?.textContent"), 10);
    if (p >= 0 && pcts.at(-1) !== p) pcts.push(p);
    await sleep(250);
  }
  const first = await b.js(`(() => { const r = performance.getEntriesByType("resource").find((e) => /assets\\/main-.*\\.js|src\\/main\\.jsx/.test(e.name)); return { fcp: Math.round(performance.getEntriesByName("first-contentful-paint")[0].startTime), js: Math.round(r.responseEnd), sp: window.__sp, inert: document.getElementById("root").inert, theme: document.querySelector('meta[name="theme-color"]').content }; })()`);
  const seq = first.sp.classes.map(([, c]) => c).join(" → ");
  check(first.fcp < first.js, `màn hiện trước khi JS tải xong: vẽ lần đầu ${first.fcp} ms, JS xong ${first.js} ms`);
  const css = await b.js(`fetch(location.href).then((r) => r.text()).then((t) => ({ lazy: /stylesheet[^>]+media="print"/.test(t) || t.includes('src/main.jsx'), media: document.querySelector('link[rel=stylesheet]')?.media ?? 'all', app: getComputedStyle(document.querySelector('.app')).position }))`);
  check(css.lazy && css.media === "all" && css.app === "relative", "CSS của app không chặn lần vẽ đầu, và vẫn được áp dụng sau đó");
  check(pcts.length >= 5 && pcts.every((p, i) => !i || p > pcts[i - 1]) && pcts.at(-1) >= 80, `% tăng dần: ${pcts.join(", ")}`);
  check(first.sp.opacity === 1, "thanh tiến độ có hiện");
  check(/slow/.test(seq) && /done/.test(seq) && /out/.test(seq), `thứ tự lớp: ${seq}`);
  check(!first.inert && first.theme === "#000000" && (await b.js("!!document.querySelector('.cam')")), `vào app lúc ${first.sp.removed} ms: hết inert, thanh trạng thái đen, có màn Kiểm tra`);

  await b.send("Network.setBypassServiceWorker", { bypass: false });
  await b.send("Network.emulateNetworkConditions", { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
  const opens = [];
  await b.send("Page.reload");  // lần này service worker lưu file lại, các lần sau mới là mở lại từ bộ nhớ đệm
  await sleep(300);
  await b.until(gone, 60000);
  for (let i = 0; i < 3; i++) {
    await b.send("Page.reload");
    await sleep(300);
    await b.until(gone, 30000);
    opens.push(await b.js("({ ...window.__sp, fcp: performance.getEntriesByName('first-contentful-paint')[0].startTime })"));
  }
  const fast = opens.every((o) => !o.classes.some(([, c]) => /done/.test(c)) && o.opacity === 0);
  check(fast, `mở lại: không có thanh, không có nhịp băng (${JSON.stringify(opens.map((o) => o.classes.map(([, c]) => c)))})`);
  const holds = opens.map((o) => Math.round(o.classes.find(([, c]) => /out/.test(c))[0] - o.fcp));
  check(holds.every((t) => t >= 1550), `mở lại: tên được giữ trên màn trước khi lớp vàng rời đi (bắt đầu rời lúc ${holds.join(", ")} ms sau lần vẽ đầu, cần ≥ 1580)`);
  console.log(`  mở lại tới lúc vào app: ${opens.map((o) => o.removed).join(", ")} ms`);
  check(b.errors.length === 0, `không lỗi trên trang${b.errors.length ? ": " + b.errors.join(" | ") : ""}`);
  b.close();
}

// 3: tải mô hình lỗi
{
  const b = await browser(9372);
  await phone(b);
  await b.send("Network.setBlockedURLs", { urls: ["*.onnx"] });
  await b.send("Page.navigate", { url });
  await b.until("document.getElementById('splash')?.classList.contains('fail')", 60000);
  const f = await b.js(`({ why: document.getElementById("sp-why").textContent, focus: document.activeElement?.id, inert: document.getElementById("root").inert, load: getComputedStyle(document.querySelector(".sp-load")).display })`);
  check(/kết nối mạng/.test(f.why) && f.focus === "sp-retry" && f.inert && f.load === "none", `lỗi mạng: "${f.why}", tiêu điểm ${f.focus}, app phía sau chưa bấm được`);
  await b.send("Network.setBlockedURLs", { urls: [] });
  await b.js("document.getElementById('sp-retry').click()");
  await sleep(500);
  await b.until(gone);
  check(await b.js("!!document.querySelector('.cam') && !document.getElementById('root').inert"), "Thử lại khi đã có mạng: vào được app");
  await b.send("Network.setBlockedURLs", { urls: ["*.onnx"] });
  await b.send("Network.setCacheDisabled", { cacheDisabled: true });
  await b.js("navigator.serviceWorker?.getRegistrations().then((rs) => Promise.all(rs.map((r) => r.unregister()))).then(() => caches.keys()).then((ks) => Promise.all(ks.map((k) => caches.delete(k))))");
  await b.send("Page.reload");
  await sleep(300);
  await b.until("document.getElementById('splash')?.classList.contains('fail')", 60000);
  await b.js("document.getElementById('sp-skip').click()");
  await b.until(gone, 5000);
  const s = await b.js("({ inert: document.getElementById('root').inert, hint: document.querySelector('.hint, .drophint')?.innerText ?? '' , thumb: !!document.querySelector('.thumb') })");
  const said = s.hint.split("\n").find((l) => /Không tải được/.test(l));
  check(!s.inert && !!said && s.thumb, `Vào app: dùng được Lịch sử, màn báo "${said?.slice(0, 60)}"`);
  b.close();
}

// 3b: mạng đứng giữa chừng, không có lỗi nào được báo về
{
  const b = await browser(9375);
  await phone(b);
  // mọi file tải kèm (mô hình, WASM) cùng đứng 24 s kể từ khối dữ liệu thứ hai đầu tiên rồi chạy tiếp; đứng riêng một file thì file kia vẫn
  // về dữ liệu và app đúng là không được báo kẹt
  await b.send("Page.addScriptToEvaluateOnNewDocument", { source: `const f = window.fetch; window.fetch = async (...a) => { const r = await f(...a); if (!/\\.onnx|\\.wasm/.test(String(a[0]))) return r; const rd = r.body.getReader(); let n = 0;
    return new Response(new ReadableStream({ async pull(c) { if (n++ >= 1) { window.__stallUntil ??= Date.now() + 24000; const w = window.__stallUntil - Date.now(); if (w > 0) await new Promise((s) => setTimeout(s, w)); } const { done, value } = await rd.read(); if (done) c.close(); else c.enqueue(value); } }), { status: r.status }); };` });
  await b.send("Page.navigate", { url });
  await b.until("document.getElementById('splash')?.classList.contains('fail')", 40000);
  const t = await b.js("({ title: document.getElementById('sp-title').textContent, at: performance.now(), inert: document.getElementById('root').inert })");
  check(/lâu hơn bình thường/.test(t.title) && t.inert, `có lối thoát lúc ${Math.round(t.at / 1000)} s: "${t.title}"`);
  await b.until("!document.getElementById('splash')?.classList.contains('fail')", 15000);
  check(await b.js("document.activeElement?.id === 'sp-rail'"), "dữ liệu chạy lại: lối thoát tự ẩn, tiêu điểm về thanh tiến độ");
  await b.until(gone, 60000);
  check(await b.js("!!document.querySelector('.cam') && !document.getElementById('root').inert"), "vẫn vào app bình thường khi tải xong");
  b.close();
  const c = await browser(9376);
  await phone(c);
  await c.send("Page.addScriptToEvaluateOnNewDocument", { source: `const f = window.fetch; window.fetch = (...a) => (/\\.onnx|\\.wasm/.test(String(a[0])) ? new Promise(() => {}) : f(...a));` });
  await c.send("Page.navigate", { url });
  await c.until("document.getElementById('splash')?.classList.contains('fail')", 40000);
  await c.js("document.getElementById('sp-skip').click()");
  await c.until(gone, 5000);
  const s = await c.js("({ inert: document.getElementById('root').inert, done: (window.__sp.classes.map(([, x]) => x).join()).includes('done') })");
  check(!s.inert && !s.done, "đứng hẳn: bấm Vào app vào được, không có nhịp băng");
  c.close();
}

// 4: Giảm chuyển động
{
  const b = await browser(9373);
  await phone(b);
  await b.send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
  await b.send("Page.navigate", { url });
  await b.until("!!document.querySelector('.sp-drop')", 30000);
  const names = await b.js("['.sp-drop', '.sp-rock', '.sp-name', '.sp-stripes'].map((s) => getComputedStyle(document.querySelector(s)).animationName).join()");
  check(names === "none,none,none,none", `không có chuyển động: ${names}`);
  await b.until(gone);
  const c = (await b.js("window.__sp")).classes.map(([, x]) => x).join(" → ");
  check(!/done/.test(c), `chỉ mờ dần, không có nhịp băng: ${c}`);
  b.close();
}

// 5: bố cục: giữ màn ở lại bằng cách cho tải mô hình không bao giờ xong
{
  const b = await browser(9374);
  await b.send("Page.addScriptToEvaluateOnNewDocument", { source: `const f = window.fetch; window.fetch = (...a) => (/\\.onnx|\\.wasm/.test(String(a[0])) ? new Promise(() => {}) : f(...a));` });
  const rect = (s) => `(() => { const r = document.querySelector("${s}").getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; })()`;
  for (const [w, h] of [[320, 568], [414, 896], [896, 414], [1440, 900]]) {
    await phone(b, w, h);
    await b.send("Page.navigate", { url });
    await b.until("!!document.querySelector('.sp-name')", 30000);
    await sleep(900);
    await b.js("document.getElementById('splash').classList.add('slow')");
    const hero = await b.js(rect(".sp-hero")), load = await b.js(rect(".sp-load"));
    const inside = (r) => r[0] >= 0 && r[1] >= 0 && r[2] <= w && r[3] <= h;
    await b.js(`(() => { const e = document.getElementById("splash"); e.classList.add("fail"); document.getElementById("sp-why").textContent = "Kiểm tra kết nối mạng rồi thử lại."; document.getElementById("sp-title").textContent = "Chưa tải được mô hình"; document.getElementById("sp-detail").textContent = "no available backend found. ERR: [wasm] RangeError: WebAssembly.Instance(): Out of memory: Cannot allocate Wasm memory for new instance at some/very/long/path/ort-wasm-simd-threaded.mjs:1234:5678 and a lot more text after that"; document.getElementById("sp-fail").hidden = false; })()`);
    const fail = await b.js(rect(".sp-fail"));
    const buttons = await b.js(`[...document.querySelectorAll(".sp-fail button")].map((x) => Math.round(x.getBoundingClientRect().height)).join()`);
    check(inside(hero) && inside(load) && hero[3] <= load[1] && inside(fail) && hero[3] <= fail[1] && buttons.split(",").every((v) => +v >= 44),
      `${w}×${h}: mũ + tên đến y=${Math.round(hero[3])}, thanh từ y=${Math.round(load[1])}, báo lỗi từ y=${Math.round(fail[1])}, nút cao ${buttons}`);
  }
  b.close();
}
clearTimeout(timer);
console.log(failed ? `${failed} chỗ SAI` : "splash: đạt");
process.exit(failed ? 1 : 0);
