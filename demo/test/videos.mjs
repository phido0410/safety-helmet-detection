// Thử chế độ Video của HelmetCheck trên video thật (không nằm trong npm test: cần Chrome và `npm run dev` đang chạy). Chrome headless,
// màn máy tính, CPU giảm tốc (vd. 1.5 → khoảng 4–8 khung/s như iPhone 11); mỗi video: mở trang, chọn Video, nạp tệp, phát hết, rồi
// xuất mọi ảnh vi phạm app đã lưu (IndexedDB) ra <outdir>/<tên video>/ (saves.json + save_<k>.jpg) và xóa lịch sử.
// Video thử (Mixkit, giấy phép miễn phí; tải về máy, không commit): data/ood/videos/mixkit_{1459,23511,31473,32296}.mp4 (OOD-1) và
//   curl -L -o mixkit_<id>.mp4 https://assets.mixkit.co/videos/<id>/<id>-720.mp4   với id 4809, 4872, 47755, 23243
//   node demo/test/videos.mjs https://localhost:8443/ <outdir> 1.5 <video.mp4> [...]
import { spawn } from "node:child_process";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename } from "node:path";
const [url, out, throttle, ...videos] = process.argv.slice(2);
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", ["--headless=new", "--remote-debugging-port=9347", "--ignore-certificate-errors",
  "--autoplay-policy=no-user-gesture-required", `--user-data-dir=${mkdtempSync(tmpdir() + "/cdpv")}`, "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let target; for (let i = 0; i < 50 && !target; i++) { await sleep(200); try { target = (await (await fetch("http://127.0.0.1:9347/json")).json()).find((t) => t.type === "page"); } catch {} }
const ws = new WebSocket(target.webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r));
let id = 0; const pending = {}, logs = [];
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id) pending[d.id]?.(d); else if (d.method === "Runtime.exceptionThrown") logs.push("EXC " + JSON.stringify(d.params.exceptionDetails).slice(0, 300)); };
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const js = async (e) => (await send("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true })).result?.result?.value;
const until = async (e, ms = 60000) => { for (let t = 0; t < ms; t += 250) { if (await js(e)) return true; await sleep(250); } throw new Error("hết giờ: " + e + "\n" + logs.join("\n")); };
const btn = (re) => `[...document.querySelectorAll('.panel .btn, .segmented button')].find((b) => ${re}.test(b.innerText))`;
const dump = `(async () => {
  const db = await new Promise((r, j) => { const q = indexedDB.open("helmetcheck", 1); q.onsuccess = () => r(q.result); q.onerror = j; });
  const all = await new Promise((r) => { const q = db.transaction("checks").objectStore("checks").getAll(); q.onsuccess = () => r(q.result); });
  const b64 = (blob) => new Promise((r) => { const f = new FileReader(); f.onload = () => r(f.result.split(",")[1]); f.readAsDataURL(blob); });
  const rows = await Promise.all(all.map(async (x) => ({ id: x.id, videoTime: x.videoTime, width: x.width, height: x.height, people: x.people, img: await b64(x.image) })));
  await new Promise((r) => { const t = db.transaction("checks", "readwrite"); t.objectStore("checks").clear(); t.oncomplete = r; });
  return rows; })()`;
await send("Runtime.enable"); await send("Page.enable"); await send("DOM.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
await send("Emulation.setCPUThrottlingRate", { rate: +throttle });
for (const v of videos) {
  await send("Page.navigate", { url }); await until(`!!${btn("/^Video$/")}`, 120000);
  await until("!document.querySelector('.drophint')?.innerText.includes('Đang tải')", 120000);
  await js(`${btn("/^Video$/")}.click()`); await sleep(300);
  const { root } = (await send("DOM.getDocument", { depth: -1 })).result;
  const { nodeId } = (await send("DOM.querySelector", { nodeId: root.nodeId, selector: "input[type=file][accept^=video]" })).result;
  await send("DOM.setFileInputFiles", { nodeId, files: [v] });
  await until(`!!${btn("/Phát/")}`); await js(`${btn("/Phát/")}.click()`);
  const t0 = Date.now();
  await until("document.querySelector('video')?.ended", 300000);
  await sleep(1500);
  const summary = await js("document.querySelector('.panel p')?.innerText ?? ''");
  const rows = await js(dump);
  const dir = `${out}/${basename(v, ".mp4")}`; mkdirSync(dir, { recursive: true });
  rows.forEach((r, k) => writeFileSync(`${dir}/save_${k + 1}.jpg`, Buffer.from(r.img, "base64")));
  writeFileSync(`${dir}/saves.json`, JSON.stringify(rows.map(({ img, ...r }) => r), null, 1));
  console.log(`${basename(v)}: ${summary} | ${rows.length} ảnh lưu tại ${rows.map((r) => `${r.videoTime.toFixed(1)}s (${r.people.filter((p) => p.violation).length} vi phạm)`).join(", ")} | ${((Date.now() - t0) / 1000).toFixed(0)} s`);
}
console.log("console:", logs.join("\n") || "(không có lỗi)");
ws.close(); chrome.kill();
