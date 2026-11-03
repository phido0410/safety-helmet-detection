// Nạp mô hình một lần cho cả ứng dụng: tải model.onnx (có tiến độ), tạo phiên onnxruntime-web, trả về hàm run(nguồn, rộng, cao).
// Chạy bằng WASM (CPU, đa luồng khi crossOriginIsolated): trên iPhone 11 Pro Max, demo/bench.html đo WASM 242 ms/khung so với
// WebGPU 273 ms ở cỡ 800 (reports/deployment/M3_yolo26n_extra/iphone11_bench.txt), lại đỡ tải thêm 27 MB thư viện WebGPU.
// onnxruntime-web nằm ở public/vendor (scripts/export_demo.py tải đúng phiên bản), nạp bằng URL lúc chạy, không qua Vite.
import { detect } from "../../detector.js";

const url = (path) => new URL(path, document.baseURI).href;
let loading;

export const loadModel = (onProgress) => (loading ??= init(onProgress));

async function fetchBytes(path, onProgress) {
  const res = await fetch(url(path));
  if (!res.ok) throw new Error(`Không tải được ${path} (${res.status})`);
  const total = Number(res.headers.get("content-length")) || 0;
  const reader = res.body.getReader(), parts = [];
  let got = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    parts.push(value);
    got += value.length;
    if (total) onProgress?.(got / total);
  }
  const bytes = new Uint8Array(got);
  parts.reduce((at, p) => (bytes.set(p, at), at + p.length), 0);
  return bytes;
}

async function init(onProgress) {
  const cfg = await (await fetch(url("model/config.json"))).json();
  const bytes = await fetchBytes(`model/${cfg.models[cfg.imgsz]}`, onProgress);
  const ort = await import(/* @vite-ignore */ url("vendor/ort.wasm.min.mjs"));
  ort.env.wasm.wasmPaths = url("vendor/");
  const session = await ort.InferenceSession.create(bytes, { executionProviders: ["wasm"] });
  const canvas = document.createElement("canvas");
  let busy = Promise.resolve();
  // session.run không chạy song song: xếp hàng các lần gọi
  const run = (source, width, height) => (busy = busy.then(async () => {
    const t = performance.now();
    const dets = await detect(ort, session, cfg, source, width, height, canvas);
    return { dets, ms: performance.now() - t };
  }));
  return { cfg, backend: "WASM", run };
}

// Chỉ giữ hai lớp người; đánh số trái sang phải như chú thích trên bản vẽ
export function people(dets, cfg) {
  const violation = cfg.violation, helmet = cfg.names.indexOf("person_with_helmet");
  return dets.filter((d) => d.cls === violation || d.cls === helmet)
    .sort((a, b) => a.box[0] - b.box[0])
    .map((d, i) => ({ n: i + 1, box: d.box, score: d.score, violation: d.cls === violation }));
}
