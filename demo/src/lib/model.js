// Nạp mô hình một lần cho cả ứng dụng: tải model.onnx và file WASM (có tiến độ), tạo phiên onnxruntime-web, trả về hàm run(nguồn, rộng, cao).
// Lần đầu mở bằng WASM (CPU, đa luồng khi crossOriginIsolated). Máy có WebGPU thì đo ngầm WebGPU so với WASM rồi chuyển nếu nhanh rõ; các lần
// sau mở thẳng bằng WebGPU, không nạp WASM (giữ cả hai tốn thêm 95 MB bộ nhớ WASM, Chrome Mac; iPhone 17 bị tắt trang rồi hết bộ nhớ khi
// tải lại, 2026-11-05). Safari
// không cho biết đời máy (iPhone 11 và 17 cùng ghi "iPhone OS 18_7", 4 nhân) mà tốc độ thì ngược nhau — bench.html ở cỡ 800: iPhone 17
// WASM 1 luồng 206 ms / WebGPU 54 ms, iPhone 11 WASM 229 / WebGPU 253 (reports/deployment/M3b_yolo26n_bg/{single_thread,iphone11}_bench.txt).
// onnxruntime-web nằm ở public/vendor (scripts/export_demo.py tải đúng phiên bản), nạp bằng URL lúc chạy, không qua Vite.
import { detect, iou } from "../../detector.js";

const url = (path) => new URL(path, document.baseURI).href;
let loading;

// Safari 26.2 treo cả trang khi chạy WASM đa luồng (iPhone 17: chỉ chạy được khi tắt đa luồng), Safari 26.6.3 chạy tốt và một luồng
// chậm 2,2 lần (iPhone 11: 506 so với 229 ms, reports/deployment/M3b_yolo26n_bg/{single_thread,iphone11}_bench.txt) → Safari 26.0–26.4 chạy một luồng. Bản chưa biết:
// đánh dấu "<thời điểm>|<user agent>" trước khi khởi tạo đa luồng, chạy thử xong thì xóa; dấu còn lại cùng user agent nghĩa là lần
// trước bị treo → một luồng. Rời trang lúc đang chạy thử (tải lại, chuyển ứng dụng) cũng để lại dấu (iPhone 11 kẹt một luồng, chậm
// gấp đôi) → rời trang thì xóa dấu (trang treo thật thì không chạy được sự kiện này), và dấu chỉ có hiệu lực HANG_TTL_MS.
const HANG_KEY = "helmetcheck-thread-hang", HANG_TTL_MS = 24 * 3600e3;
const hung = (mark, ua, now) => {
  const i = mark?.indexOf("|") ?? -1;  // dấu kiểu cũ (chỉ có user agent) coi như hết hạn
  return i > 0 && mark.slice(i + 1) === ua && now - Number(mark.slice(0, i)) < HANG_TTL_MS;
};
export const singleThread = (ua, mark, now = Date.now()) => /Version\/26\.[0-4]\b/.test(ua) || hung(mark, ua, now);
// WebGPU chỉ được chọn khi nhanh rõ (dưới GPU_GAIN thời gian WASM) để không đổi qua lại vì sai số; lựa chọn nhớ theo user agent (cập
// nhật Safari thì đo lại); chạy thử WebGPU cũng đánh dấu chống treo như đa luồng (GPU_KEY).
const PICK_KEY = "helmetcheck-backend", GPU_KEY = "helmetcheck-gpu-hang", GPU_GAIN = 0.8, BENCH_RUNS = 3, CAPTURE_RUNS = 3;
export const pickBackend = (wasmMs, gpuMs) => (gpuMs < GPU_GAIN * wasmMs ? "webgpu" : "wasm");
function stored(key, value) {
  try {
    if (value === undefined) return localStorage.getItem(key);
    value ? localStorage.setItem(key, value) : localStorage.removeItem(key);
  } catch { return null; }  // bộ nhớ trình duyệt bị chặn (duyệt riêng tư): chỉ còn quy tắc theo phiên bản, đo lại mỗi lần mở
}
const hangMark = (value) => stored(HANG_KEY, value);
const median = (xs) => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];

// Graph capture: ONNX Runtime ghi lại lệnh GPU rồi phát lại, các khung sau không tạo bind group và buffer mới. Không có nó Safari 26.2
// tắt trang sau 5–21 s camera, có nó chạy hơn 3 phút (iPhone 17, demo/stress.html). Bắt buộc đầu vào, đầu ra là GPU buffer có sẵn.
export const GPU_OPTIONS = { executionProviders: [{ name: "webgpu", enableGraphCapture: true }], enableGraphCapture: true };
export function captureInfer(ort, session) {
  const device = ort.env.webgpu.device, U = GPUBufferUsage, [inDims, outDims] = [session.inputMetadata[0].shape, session.outputMetadata[0].shape];
  const bytesOf = (dims) => dims.reduce((a, b) => a * b) * 4, size = bytesOf(outDims);
  const input = device.createBuffer({ size: bytesOf(inDims), usage: U.STORAGE | U.COPY_DST | U.COPY_SRC });
  const output = device.createBuffer({ size, usage: U.STORAGE | U.COPY_DST | U.COPY_SRC }), stage = device.createBuffer({ size, usage: U.MAP_READ | U.COPY_DST });
  const feeds = { [session.inputNames[0]]: ort.Tensor.fromGpuBuffer(input, { dataType: "float32", dims: inDims }) };
  const fetches = { [session.outputNames[0]]: ort.Tensor.fromGpuBuffer(output, { dataType: "float32", dims: outDims }) };
  return async (data) => {
    device.queue.writeBuffer(input, 0, data);
    await session.run(feeds, fetches);
    const enc = device.createCommandEncoder();
    enc.copyBufferToBuffer(output, 0, stage, 0, size);
    device.queue.submit([enc.finish()]);
    await stage.mapAsync(GPUMapMode.READ);
    const out = new Float32Array(stage.getMappedRange().slice(0));
    stage.unmap();
    return out;
  };
}

// onBackend(nhãn): gọi khi app chuyển sang WebGPU sau lúc đã mở bằng WASM
export const loadModel = (onProgress, onBackend) => (loading ??= init(onProgress, onBackend));

async function fetchBytes(path, onChunk) {
  const res = await fetch(url(path));
  if (!res.ok) throw new Error(`Không tải được ${path} (${res.status})`);
  const reader = res.body.getReader(), parts = [];
  let got = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    parts.push(value);
    got += value.length;
    onChunk(value.length);
  }
  const bytes = new Uint8Array(got);
  parts.reduce((at, p) => (bytes.set(p, at), at + p.length), 0);
  return bytes;
}

// Phiên WASM (CPU). tag: chuỗi thêm vào URL để nạp bản onnxruntime-web mới khi thử lại (bản đã lỗi ghi nhớ lỗi, không khởi tạo lại).
async function openWasm(bytes, wasm, ua, s, blank, tag) {
  const ort = await import(/* @vite-ignore */ url(`vendor/ort.wasm.min.mjs${tag}`));
  ort.env.wasm.wasmPaths = url("vendor/");
  ort.env.wasm.wasmBinary = wasm;
  const one = singleThread(ua, hangMark()), leave = () => hangMark(null);
  if (one) ort.env.wasm.numThreads = 1;
  else { hangMark(`${Date.now()}|${ua}`); addEventListener("pagehide", leave); document.addEventListener("visibilitychange", leave); }
  try {
    const session = await ort.InferenceSession.create(bytes, { executionProviders: ["wasm"] });
    const infer = async (data) => (await session.run({ [session.inputNames[0]]: new ort.Tensor("float32", data, [1, 3, s, s]) }))[session.outputNames[0]].data;
    await infer(blank);  // chạy thử một lần: nếu đa luồng bị treo thì treo ở đây, khi dấu còn đó (lỗi thì không phải treo, xóa dấu)
    return { infer, release: () => session.release(), label: `WASM, ${one || !self.crossOriginIsolated ? 1 : ort.env.wasm.numThreads} luồng` };
  } finally {
    if (!one) { leave(); removeEventListener("pagehide", leave); document.removeEventListener("visibilitychange", leave); }
  }
}

// Phiên WebGPU một luồng CPU: phần nặng nằm ở GPU, và Safari 26.2 treo khi chạy WASM đa luồng (iPhone 17 đo WebGPU 54 ms ở một luồng).
async function openGpu(bytes) {
  const gort = await import(/* @vite-ignore */ url("vendor/ort.webgpu.min.mjs"));
  Object.assign(gort.env.wasm, { wasmPaths: url("vendor/"), numThreads: 1 });
  return { infer: captureInfer(gort, await gort.InferenceSession.create(bytes, GPU_OPTIONS)), label: "WebGPU" };
}

// iPhone 17 (2026-11-05): trang bị tắt rồi tải lại ngay thì tạo bộ nhớ WASM báo "RangeError: Out of memory", bộ nhớ của trang cũ chưa được
// trả. Chờ OOM_WAIT_MS rồi thử lại một lần bằng bản onnxruntime-web nạp mới; vẫn lỗi thì báo cách xử lý thay cho lỗi kỹ thuật.
const OOM = /out of memory/i, OOM_WAIT_MS = 1500;
export const OOM_MESSAGE = "máy đang thiếu bộ nhớ. Đóng bớt tab Safari rồi tải lại trang";
export async function retryOom(open, wait = OOM_WAIT_MS) {
  try { return await open(""); } catch (e) {
    if (!OOM.test(String(e?.message ?? e))) throw e;
  }
  await new Promise((r) => setTimeout(r, wait));
  try { return await open("?retry=1"); } catch (e) {
    throw OOM.test(String(e?.message ?? e)) ? new Error(OOM_MESSAGE) : e;
  }
}

// Lúc đang dùng WebGPU trang bị tắt thì dấu còn lại (ẩn trang, rời trang là xóa): lần mở sau chạy WASM, không sập lặp lại.
function armGpu(ua) {
  const armed = () => stored(GPU_KEY, document.hidden ? null : `${Date.now()}|${ua}`);
  armed();
  document.addEventListener("visibilitychange", armed);
  addEventListener("pagehide", () => stored(GPU_KEY, null));
}

// Tải mô hình (và file WASM của onnxruntime-web nếu cần) cùng lúc, % tính trên tổng dung lượng chưa nén ghi trong config.json (Vercel nén
// brotli nên không có content-length); file WASM đưa thẳng cho onnxruntime-web để nó không tải lại.
async function init(onProgress, onBackend) {
  // ?v=2: service worker bản trước lấy bộ đệm trước cả config.json, đã lưu bản chưa có `bytes`; đường dẫn mới thì nó phải tải lại
  const cfg = await (await fetch(url("model/config.json?v=2"))).json();
  const ua = navigator.userAgent, saved = JSON.parse(stored(PICK_KEY) ?? "null"), known = saved?.ua === ua ? saved.backend : null;
  const gpuOff = hung(stored(GPU_KEY), ua, Date.now()), direct = !!navigator.gpu && known === "webgpu" && !gpuOff;
  const model = `model/${cfg.models[cfg.imgsz]}`, total = cfg.bytes[model] + (direct ? 0 : cfg.bytes[cfg.wasm]);
  let got = 0;
  const tick = (n) => onProgress?.(Math.min(1, (got += n) / total));
  const [bytes, wasm] = await Promise.all([fetchBytes(model, tick), direct ? null : fetchBytes(cfg.wasm, tick)]);
  const s = cfg.imgsz, blank = new Float32Array(3 * s * s);
  let active = null;
  if (direct) {
    stored(GPU_KEY, `${Date.now()}|${ua}`);
    try {
      active = await openGpu(bytes);
      for (let k = 0; k < CAPTURE_RUNS; k++) await active.infer(blank);  // làm nóng: biên dịch shader, ghi lại lệnh GPU
      armGpu(ua);
    } catch { stored(GPU_KEY, null); active = null; }  // lỗi (không phải treo): dùng WASM lần này, lần sau thử lại
  }
  if (!active) {
    const bin = wasm ?? await fetchBytes(cfg.wasm, () => {});
    active = await retryOom((tag) => openWasm(bytes, bin, ua, s, blank, tag));
    // máy có WebGPU mà lần trước trang bị tắt khi đang chạy WebGPU: hiện để biết vì sao chậm (Xóa dữ liệu đã tải để bật lại)
    if (navigator.gpu && known !== "wasm" && gpuOff) active.label += " (WebGPU tạm tắt)";
  }
  const canvas = document.createElement("canvas");
  let busy = Promise.resolve();
  // session.run không chạy song song: xếp hàng mọi lần gọi (cả lúc đo WebGPU); một lần lỗi không làm hỏng các lần sau
  const queue = (fn) => { const p = busy.then(fn, fn); busy = p.catch(() => {}); return p; };
  const run = (source, width, height) => queue(async () => {
    const t = performance.now();
    const dets = await detect(active.infer, cfg, source, width, height, canvas);
    return { dets, ms: performance.now() - t };
  });
  const time = (o) => queue(async () => {
    const ms = [];
    for (let k = 0; k < BENCH_RUNS; k++) { const t = performance.now(); await o.infer(blank); ms.push(performance.now() - t); }
    return median(ms);
  });
  // Lần đầu: đo ngầm sau khi app đã dùng được bằng WASM (không chặn lần mở đầu; thư viện WebGPU nặng thêm 27 MB)
  async function tryGpu() {
    if (direct || !navigator.gpu || known || gpuOff) return;
    stored(GPU_KEY, `${Date.now()}|${ua}`);
    try {
      const gpu = await openGpu(bytes);
      await queue(async () => { for (let k = 0; k < CAPTURE_RUNS; k++) await gpu.infer(blank); });
      stored(GPU_KEY, null);
      const ms = { wasm: await time(active), webgpu: await time(gpu) }, pick = pickBackend(ms.wasm, ms.webgpu);
      stored(PICK_KEY, JSON.stringify({ ua, backend: pick, ms }));
      if (pick !== "webgpu") return;
      const cpu = active;
      active = gpu;
      onBackend?.(gpu.label);
      queue(() => cpu.release());  // phiên WASM không còn dùng tới (bộ nhớ WASM của nó vẫn giữ tới khi tải lại trang)
      armGpu(ua);
    } catch { stored(GPU_KEY, null); }  // không tạo được phiên WebGPU (lỗi, không phải treo): giữ WASM, lần sau thử lại
  }
  tryGpu();
  return { cfg, backend: active.label, run };
}

// Chỉ giữ hai lớp người; đánh số trái sang phải như chú thích trên bản vẽ. NMS chỉ lọc trong từng lớp nên một người có thể còn cả
// hộp có mũ lẫn hộp không mũ (val SHEL5K, M3b: 31/33 cặp như vậy có IoU > 0,7 là cùng một người, 0 cặp là hai người) → giữ hộp
// điểm cao hơn (eval_min_size.py --dup-rule score), để mỗi người một khung và tracker không coi là hai người. Bản đầu luôn giữ hộp
// không mũ: người đội mũ rõ ("có mũ" 0,78) bị báo vi phạm chỉ vì một hộp "không mũ" 0,40 trùng lên.
// Quy tắc bộ phận – toàn thể (khi config có parts, scripts/eval_part_rule.py): mô hình phát hiện người từ nửa người trở lên, nên
// khung người chỉ được giữ khi có tâm một khung đầu / mặt / mũ (điểm ≥ partConf) nằm trong nó; ảnh chỉ có chân, bàn phím… bị loại.
// Người ở xa (khung thấp hơn cfg.minHeight px trên ảnh đưa vào mô hình, scripts/eval_min_size.py) vẫn được trả về để khoanh mờ,
// nhưng không tính là vi phạm, không tự lưu: dưới mức đó mô hình đoán sai nhiều và ảnh không dùng làm bằng chứng được.
export function people(dets, cfg, width, height) {
  const violation = cfg.violation, helmet = cfg.names.indexOf("person_with_helmet");
  // chiều cao hiệu dụng (eval_min_size.py --height effective): ảnh nhỏ bị phóng to lên imgsz không thêm chi tiết nên tính trên ảnh gốc
  const far = ([, y1, , y2]) => cfg.minHeight > 0 && (y2 - y1) * Math.min(1, cfg.imgsz / Math.max(width, height)) < cfg.minHeight;
  const parts = cfg.parts ? dets.filter((d) => cfg.parts.includes(d.cls) && d.score >= cfg.partConf)
    .map(({ box: [x1, y1, x2, y2] }) => [(x1 + x2) / 2, (y1 + y2) / 2]) : null;
  const hasPart = ({ box: [x1, y1, x2, y2] }) => !parts || parts.some(([cx, cy]) => cx >= x1 && cx <= x2 && cy >= y1 && cy <= y2);
  const persons = dets.filter((d) => (d.cls === violation || d.cls === helmet) && hasPart(d));
  return persons.filter((d) => !persons.some((o) => o.cls !== d.cls && o.score > d.score && iou(o.box, d.box) > cfg.iou))
    .sort((a, b) => a.box[0] - b.box[0])
    .map((d, i) => (far(d.box) ? { n: i + 1, box: d.box, score: d.score, violation: false, far: true }
      : { n: i + 1, box: d.box, score: d.score, violation: d.cls === violation }));
}
