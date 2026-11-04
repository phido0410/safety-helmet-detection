// Nạp mô hình một lần cho cả ứng dụng: tải model.onnx và file WASM (có tiến độ), tạo phiên onnxruntime-web, trả về hàm run(nguồn, rộng, cao).
// Chạy bằng WASM (CPU, đa luồng khi crossOriginIsolated): trên iPhone 11 Pro Max, demo/bench.html đo WASM 242 ms/khung so với
// WebGPU 273 ms ở cỡ 800 (reports/deployment/M3_yolo26n_extra/iphone11_bench.txt), lại đỡ tải thêm 27 MB thư viện WebGPU.
// onnxruntime-web nằm ở public/vendor (scripts/export_demo.py tải đúng phiên bản), nạp bằng URL lúc chạy, không qua Vite.
import { detect, iou } from "../../detector.js";

const url = (path) => new URL(path, document.baseURI).href;
let loading;

// Safari 26.2 treo cả trang khi chạy WASM đa luồng (iPhone 17: chỉ chạy được khi tắt đa luồng), Safari 26.6.3 chạy tốt và một luồng
// chậm 2,2 lần (iPhone 11: 506 so với 229 ms, reports/deployment/M3b_yolo26n_bg/{single_thread,iphone11}_bench.txt) → Safari 26.0–26.4 chạy một luồng. Bản chưa biết:
// đánh dấu trước khi khởi tạo đa luồng, chạy thử xong thì xóa; dấu còn lại cùng user agent nghĩa là lần trước bị treo → một luồng.
const HANG_KEY = "helmetcheck-thread-hang";
export const singleThread = (ua, hungUa) => /Version\/26\.[0-4]\b/.test(ua) || hungUa === ua;
function hangMark(value) {
  try {
    if (value === undefined) return localStorage.getItem(HANG_KEY);
    value ? localStorage.setItem(HANG_KEY, value) : localStorage.removeItem(HANG_KEY);
  } catch { return null; }  // bộ nhớ trình duyệt bị chặn (duyệt riêng tư): chỉ còn quy tắc theo phiên bản
}

export const loadModel = (onProgress) => (loading ??= init(onProgress));

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

// Tải mô hình và file WASM của onnxruntime-web cùng lúc, % tính trên tổng dung lượng chưa nén ghi trong config.json (Vercel nén
// brotli nên không có content-length); file WASM đưa thẳng cho onnxruntime-web để nó không tải lại.
async function init(onProgress) {
  // ?v=2: service worker bản trước lấy bộ đệm trước cả config.json, đã lưu bản chưa có `bytes`; đường dẫn mới thì nó phải tải lại
  const cfg = await (await fetch(url("model/config.json?v=2"))).json();
  const model = `model/${cfg.models[cfg.imgsz]}`, total = cfg.bytes[model] + cfg.bytes[cfg.wasm];
  let got = 0;
  const tick = (n) => onProgress?.(Math.min(1, (got += n) / total));
  const [bytes, wasm] = await Promise.all([fetchBytes(model, tick), fetchBytes(cfg.wasm, tick)]);
  const ort = await import(/* @vite-ignore */ url("vendor/ort.wasm.min.mjs"));
  ort.env.wasm.wasmPaths = url("vendor/");
  ort.env.wasm.wasmBinary = wasm;
  const ua = navigator.userAgent, one = singleThread(ua, hangMark());
  if (one) ort.env.wasm.numThreads = 1;
  else hangMark(ua);
  const session = await ort.InferenceSession.create(bytes, { executionProviders: ["wasm"] });
  const s = cfg.imgsz;  // chạy thử một lần: nếu đa luồng bị treo thì treo ở đây, khi dấu còn đó
  await session.run({ [session.inputNames[0]]: new ort.Tensor("float32", new Float32Array(3 * s * s), [1, 3, s, s]) });
  if (!one) hangMark(null);
  const canvas = document.createElement("canvas");
  let busy = Promise.resolve();
  // session.run không chạy song song: xếp hàng các lần gọi
  const run = (source, width, height) => (busy = busy.then(async () => {
    const t = performance.now();
    const dets = await detect(ort, session, cfg, source, width, height, canvas);
    return { dets, ms: performance.now() - t };
  }));
  return { cfg, backend: one ? "WASM, 1 luồng" : "WASM", run };
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
