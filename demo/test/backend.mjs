// Chọn cách chạy khi mở app (src/lib/model.js) trên Chrome: lần đầu WASM rồi chuyển WebGPU; tải lại thì mở thẳng WebGPU, không tạo bộ nhớ
// WASM thừa; lần trước trang bị tắt khi đang dùng WebGPU thì chạy WASM, ghi "(WebGPU tạm tắt)"; tạo bộ nhớ WASM báo "Out of memory" một lần
// thì thử lại được, hai lần thì báo cách xử lý. Không nằm trong npm test: cần Chrome và `npm run dev` đang chạy.
//   node demo/test/backend.mjs https://localhost:8443/
import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
const [url] = process.argv.slice(2);
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", ["--headless=new", "--remote-debugging-port=9359", "--ignore-certificate-errors",
  "--enable-unsafe-webgpu", `--user-data-dir=${mkdtempSync(tmpdir() + "/cdpb")}`, "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let target; for (let i = 0; i < 50 && !target; i++) { await sleep(200); try { target = (await (await fetch("http://127.0.0.1:9359/json")).json()).find((t) => t.type === "page"); } catch {} }
const ws = new WebSocket(target.webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r));
let id = 0, failed = 0; const pending = {};
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id) pending[d.id]?.(d); };
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const js = async (e) => (await send("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true })).result?.result?.value;
const check = (ok, msg) => { if (!ok) { failed++; console.log("SAI:", msg); } };
await send("Runtime.enable"); await send("Page.enable");
await send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
await send("Emulation.setDeviceMetricsOverride", { width: 414, height: 896, deviceScaleFactor: 2, mobile: true });
// đếm bộ nhớ WebAssembly app tạo ra; `oomLeft` lần tạo bộ nhớ dùng chung (bản WASM đa luồng) đầu tiên ném lỗi như Safari khi thiếu bộ nhớ
// `fakeCrash`: giả lập trang bị tắt lúc đang dùng WebGPU: đặt dấu ngay đầu trang mới (tải lại bình thường thì pagehide đã xóa dấu)
await send("Page.addScriptToEvaluateOnNewDocument", { source: `window.mems = 0; const W = WebAssembly, M = W.Memory;
  if (localStorage.getItem('fakeCrash')) localStorage.setItem('helmetcheck-gpu-hang', Date.now() + '|' + navigator.userAgent);
  W.Memory = function (d) { if (d?.shared && Number(localStorage.getItem('oomLeft')) > 0) { localStorage.setItem('oomLeft', Number(localStorage.getItem('oomLeft')) - 1); throw new RangeError('Out of memory'); }
    window.mems++; return new M(d); }; W.Memory.prototype = M.prototype;` });
const settled = `(() => { const t = document.body.innerText; return t.includes('Không tải được mô hình') || (!!document.querySelector('.cam') && !t.includes('Đang tải mô hình')); })()`;
const open = async () => { for (let t = 0; t < 120000 && !(await js(settled)); t += 250) await sleep(250); };
const info = () => js(`(async () => { [...document.querySelectorAll('button[aria-label="Thông tin"]')].find((b) => b.offsetParent)?.click(); await new Promise((r) => setTimeout(r, 400));
  const t = (document.querySelector('.sheet')?.innerText || '').split('\\n'); [...document.querySelectorAll('.sheet button')].find((b) => /Xong/.test(b.innerText))?.click();
  await new Promise((r) => setTimeout(r, 200)); return t[t.indexOf('Chạy trên') + 1] ?? ''; })()`);
const until = async (re, ms) => { let v = ""; for (let t = 0; t < ms && !re.test(v); t += 1000) { await sleep(1000); v = await info(); } return v; };
const load = async (setup = "") => { if (setup) await js(setup); await send("Page.reload"); await sleep(500); await open(); };

await send("Page.navigate", { url }); await open();
let v = await until(/WebGPU/, 40000);
check(v === "WebGPU" && (await js("window.mems")) === 2, `mở lần đầu: "${v}", ${await js("window.mems")} bộ nhớ WASM (phải WebGPU, 2: WASM để đo + WebGPU)`);

const t0 = Date.now(); await load(); v = await info();
check(v === "WebGPU" && (await js("window.mems")) === 1, `tải lại: "${v}", ${await js("window.mems")} bộ nhớ WASM (phải WebGPU ngay, 1)`);
console.log(`tải lại: ${v} sau ${((Date.now() - t0) / 1000).toFixed(1)} s, ${await js("window.mems")} bộ nhớ WASM`);

const crash = `localStorage.setItem('fakeCrash', 1)`;
await load(crash); v = await info();
check(/^WASM, \d luồng \(WebGPU tạm tắt\)$/.test(v), `sau khi trang bị tắt lúc dùng WebGPU: "${v}" (phải WASM, ghi WebGPU tạm tắt)`);

await load(`${crash}; localStorage.setItem('oomLeft', 1)`); v = await info();
const left = await js("localStorage.getItem('oomLeft')");
check(left === "0" && /^WASM, \d luồng \(WebGPU tạm tắt\)$/.test(v), `hết bộ nhớ một lần: "${v}", lỗi giả lập còn ${left} (phải thử lại được, WASM)`);

await load(`${crash}; localStorage.setItem('oomLeft', 2)`);
const err = await js("document.body.innerText.includes('Không tải được mô hình: máy đang thiếu bộ nhớ')");
check(err, `hết bộ nhớ hai lần: không thấy lời nhắn thiếu bộ nhớ (${(await js("document.body.innerText")).slice(0, 120)})`);

// WebGPU đang chạy bình thường mà lỗi thiếu bộ nhớ (bản WebGPU cũng tạo bộ nhớ dùng chung): không mở được WebGPU thì về WASM, vẫn chạy
await load(`localStorage.removeItem('fakeCrash'); localStorage.removeItem('helmetcheck-gpu-hang'); localStorage.setItem('oomLeft', 1)`); v = await info();
check(/^WASM, \d luồng$/.test(v), `WebGPU lỗi thiếu bộ nhớ: "${v}" (phải về WASM)`);

ws.close(); chrome.kill();
console.log(`backend: 6 tình huống: ${failed ? `${failed} chỗ SAI` : "đạt"}`);
process.exit(failed ? 1 : 0);
