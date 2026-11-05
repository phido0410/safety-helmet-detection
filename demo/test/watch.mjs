// Xem một video trong ứng dụng như người xem (chế độ Video, màn máy tính, Chrome): mỗi ~100 ms ghi dòng kết luận đang hiện; hết video thì
// đọc các ảnh ứng dụng đã lưu rồi xóa lịch sử. Chạy `lần` lượt trên cùng một hồ sơ Chrome (như dùng thật: lần đầu đo rồi chọn cách chạy).
// In mỗi lượt: ảnh đã lưu (giây, số vi phạm / số người), tỉ lệ thời gian của từng dòng kết luận, các đoạn dòng kết luận khác `mong đợi`
// dài từ 0,5 s. Không nằm trong npm test: cần Chrome và trang đang chạy (`npm run dev` hoặc bản đã đăng).
//   node demo/test/watch.mjs <url> <video.mp4> <lần> "<dòng kết luận mong đợi>"
import { spawn, execFileSync } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename } from "node:path";
const [url, video, runs = "3", expect = ""] = process.argv.slice(2);
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", MIN_SEG = 0.5;
const chrome = spawn(CHROME, ["--headless=new", "--remote-debugging-port=9360", "--ignore-certificate-errors", "--autoplay-policy=no-user-gesture-required",
  `--user-data-dir=${mkdtempSync(tmpdir() + "/cdpw")}`, "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let target; for (let i = 0; i < 50 && !target; i++) { await sleep(200); try { target = (await (await fetch("http://127.0.0.1:9360/json")).json()).find((t) => t.type === "page"); } catch {} }
const ws = new WebSocket(target.webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r));
let id = 0; const pending = {}, logs = [];
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id) pending[d.id]?.(d); else if (d.method === "Runtime.exceptionThrown") logs.push(JSON.stringify(d.params.exceptionDetails).slice(0, 300)); };
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const js = async (e) => (await send("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true })).result?.result?.value;
const until = async (e, ms = 120000) => { for (let t = 0; t < ms; t += 250) { if (await js(e)) return; await sleep(250); } throw new Error(`hết giờ: ${e}\n${logs.join("\n")}`); };
const btn = (re) => `[...document.querySelectorAll('.panel .btn, .segmented button')].find((b) => ${re}.test(b.innerText))`;
const vi = (x, d = 1) => x.toFixed(d).replace(".", ",");
await send("Runtime.enable"); await send("Page.enable"); await send("DOM.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
const version = execFileSync(CHROME, ["--version"]).toString().trim();
console.log(`${basename(video)} trên ${url} (${version}, màn 1440×900), ${runs} lượt, ${new Date().toISOString().slice(0, 10)}`);
for (let k = 1; k <= +runs; k++) {
  await send("Page.navigate", { url }); await until(`!!${btn("/^Video$/")}`);
  await until("!document.querySelector('.drophint')?.innerText.includes('Đang tải')");
  await sleep(5000);  // chờ ứng dụng đo và chọn cách chạy như lúc dùng thật
  const backend = await js(`(async () => { [...document.querySelectorAll('button[aria-label="Thông tin"]')].find((b) => b.offsetParent)?.click();
    await new Promise((r) => setTimeout(r, 400)); const t = (document.querySelector('.sheet')?.innerText || '').split('\\n');
    [...document.querySelectorAll('.sheet button')].find((b) => /Xong/.test(b.innerText))?.click(); return t[t.indexOf('Chạy trên') + 1]; })()`);
  await js(`${btn("/^Video$/")}.click()`); await sleep(300);
  const { root } = (await send("DOM.getDocument", { depth: -1 })).result;
  const { nodeId } = (await send("DOM.querySelector", { nodeId: root.nodeId, selector: "input[type=file][accept^=video]" })).result;
  await send("DOM.setFileInputFiles", { nodeId, files: [video] });
  await until(`!!${btn("/Phát/")}`); await js(`${btn("/Phát/")}.click()`);
  const rows = [];
  for (;;) {
    const r = await js(`(() => { const v = document.querySelector('video'); return { t: v.currentTime, end: v.ended, verdict: document.querySelector('.verdict h2')?.innerText ?? '' }; })()`);
    if (r.end) break;
    rows.push(r); await sleep(100);
  }
  const saves = await js(`(async () => { const db = await new Promise((r, j) => { const q = indexedDB.open("helmetcheck", 1); q.onsuccess = () => r(q.result); q.onerror = j; });
    const all = await new Promise((r) => { const q = db.transaction("checks").objectStore("checks").getAll(); q.onsuccess = () => r(q.result); });
    await new Promise((r) => { const t = db.transaction("checks", "readwrite"); t.objectStore("checks").clear(); t.oncomplete = r; });
    return all.map((x) => ({ t: x.videoTime, bad: x.people.filter((p) => p.violation).length, n: x.people.length })); })()`);
  const share = {}, segs = [];
  let cur = null;
  rows.forEach((a, i) => {
    const b = rows[i + 1]; if (!b) return;
    share[a.verdict] = (share[a.verdict] ?? 0) + (b.t - a.t);
    if (!cur || cur.v !== a.verdict) { if (cur) segs.push(cur); cur = { v: a.verdict, from: a.t, to: b.t }; } else cur.to = b.t;
  });
  if (cur) segs.push(cur);
  const total = Object.values(share).reduce((s, x) => s + x, 0);
  console.log(`lượt ${k} (${backend}): ${saves.length} ảnh lưu: ${saves.map((s) => `${vi(s.t)} s (${s.bad} vi phạm / ${s.n} người)`).join(", ") || "không có"}`);
  console.log(`  dòng kết luận: ${Object.entries(share).sort((a, b) => b[1] - a[1]).map(([v, s]) => `"${v}" ${Math.round((100 * s) / total)}%`).join(", ")}`);
  if (expect) console.log(`  khác "${expect}" từ ${vi(MIN_SEG)} s: ${segs.filter((s) => s.v !== expect && s.to - s.from >= MIN_SEG).map((s) => `"${s.v}" ${vi(s.from)}–${vi(s.to)} s`).join(", ") || "không có"}`);
}
console.log(`lỗi trên trang: ${logs.length}`);
ws.close(); chrome.kill();
