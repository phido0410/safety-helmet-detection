// Graph capture (WebGPU phát lại lệnh đã ghi) có cho đúng kết quả không: cùng dãy ảnh thật, phiên WebGPU thường và phiên graph capture
// phải ra đầu ra như nhau, và ảnh đổi thì đầu ra đổi (phát lại không dùng lại đầu vào cũ). Không nằm trong npm test: cần Chrome và
// `npm run dev` đang chạy.
//   node demo/test/capture.mjs https://localhost:8443/ <ảnh.jpg|png> [...]
import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { extname } from "node:path";
const [url, ...images] = process.argv.slice(2);
const TOL = 1e-3;
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", ["--headless=new", "--remote-debugging-port=9354", "--ignore-certificate-errors", "--enable-unsafe-webgpu", `--user-data-dir=${mkdtempSync(tmpdir() + "/cdpg")}`, "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let target; for (let i = 0; i < 50 && !target; i++) { await sleep(200); try { target = (await (await fetch("http://127.0.0.1:9354/json")).json()).find((t) => t.type === "page"); } catch {} }
const ws = new WebSocket(target.webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r));
let id = 0; const pending = {};
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id) pending[d.id]?.(d); };
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
await send("Runtime.enable"); await send("Page.enable");
await send("Page.navigate", { url: new URL("stress.html", url).href }); await sleep(1500);
const uris = images.map((p) => `data:image/${extname(p).slice(1).replace("jpg", "jpeg")};base64,${readFileSync(p).toString("base64")}`);
const r = await send("Runtime.evaluate", { awaitPromise: true, returnByValue: true, expression: `(async (uris) => {
  const { preprocess, postprocess } = await import("/detector.js"), { captureInfer, GPU_OPTIONS } = await import("/src/lib/model.js");
  const cfg = await (await fetch("/model/config.json")).json(), s = cfg.imgsz, shape = [1, 3, s, s];
  const ort = await import("/vendor/ort.webgpu.min.mjs");
  Object.assign(ort.env.wasm, { wasmPaths: new URL("/vendor/", location.href).href, numThreads: 1 });
  const bytes = new Uint8Array(await (await fetch("/model/model.onnx")).arrayBuffer());
  const plain = await ort.InferenceSession.create(bytes, { executionProviders: ["webgpu"] });
  const infer = captureInfer(ort, await ort.InferenceSession.create(bytes, GPU_OPTIONS));
  const runPlain = async (d) => (await plain.run({ [plain.inputNames[0]]: new ort.Tensor("float32", d, shape) }))[plain.outputNames[0]].data;
  const canvas = document.createElement("canvas"), inputs = [];
  for (const u of uris) { const img = new Image(); img.src = u; await img.decode(); inputs.push(preprocess(img, img.naturalWidth, img.naturalHeight, s, canvas).data); }
  const rows = []; let prev;
  for (const d of [...inputs, ...inputs.slice().reverse()]) {
    const a = await runPlain(d), b = await infer(d); let max = 0, moved = 0;
    for (let i = 0; i < a.length; i++) { max = Math.max(max, Math.abs(a[i] - b[i])); if (prev) moved = Math.max(moved, Math.abs(b[i] - prev[i])); }
    rows.push({ max, moved, boxes: [postprocess(a, cfg.names.length, cfg).length, postprocess(b, cfg.names.length, cfg).length] });
    prev = b;
  }
  return rows;
})(${JSON.stringify(uris)})` });
ws.close(); chrome.kill();
const rows = r.result?.result?.value;
if (!rows) { console.log(JSON.stringify(r.result?.exceptionDetails).slice(0, 800)); process.exit(1); }
const worst = Math.max(...rows.map((x) => x.max)), same = rows.every((x) => x.boxes[0] === x.boxes[1]);
const fresh = rows.slice(1, images.length).every((x) => x.moved > TOL);  // các ảnh khác nhau nối tiếp: đầu ra phải đổi
console.log(`${rows.length} lần chạy trên ${images.length} ảnh, ${rows.reduce((a, x) => a + x.boxes[1], 0)} hộp: lệch tối đa ${worst.toExponential(2)}, số hộp ${same ? "như nhau" : "KHÁC"}, đầu ra ${fresh ? "đổi theo ảnh" : "KHÔNG đổi theo ảnh"}`);
process.exit(worst <= TOL && same && fresh ? 0 : 1);
