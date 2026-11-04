// Tiền xử lý và hậu xử lý cho mô hình ONNX (nhánh một-nhiều của YOLO26), viết lại đúng các bước của Ultralytics 8.4.164:
// LetterBox (data/augment.py), non_max_suppression (utils/nms.py), scale_boxes (utils/ops.py).
// Kiểm tra khớp với Ultralytics: node demo/test/run.mjs (dữ liệu mẫu do scripts/export_demo.py --fixtures sinh ra).

// round() của Python 3 làm tròn nửa về số chẵn; Math.round thì làm tròn nửa lên
export const pyRound = (x) => {
  const f = Math.floor(x), d = x - f;
  return d > 0.5 || (d === 0.5 && f % 2 !== 0) ? f + 1 : f;
};

// Thông số letterbox (center = True, auto = False): tỉ lệ thu nhỏ, kích thước sau thu nhỏ, lề trái/trên
export function letterbox(width, height, size) {
  const r = Math.min(size / height, size / width);
  const newW = pyRound(width * r), newH = pyRound(height * r);
  const left = pyRound((size - newW) / 2 - 0.1), top = pyRound((size - newH) / 2 - 0.1);
  return { r, newW, newH, left, top };
}

// Ảnh (ảnh, khung video, canvas) → tensor Float32 1×3×size×size, RGB, giá trị 0–1, lề màu (114, 114, 114)
export function preprocess(source, width, height, size, canvas) {
  const lb = letterbox(width, height, size);
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.fillStyle = "rgb(114, 114, 114)";
  ctx.fillRect(0, 0, size, size);
  ctx.drawImage(source, lb.left, lb.top, lb.newW, lb.newH);
  const px = ctx.getImageData(0, 0, size, size).data, n = size * size;
  const data = new Float32Array(3 * n);
  for (let i = 0; i < n; i++) {
    data[i] = px[4 * i] / 255;
    data[n + i] = px[4 * i + 1] / 255;
    data[2 * n + i] = px[4 * i + 2] / 255;
  }
  return { data, lb };
}

export const iou = (a, b) => {
  const w = Math.min(a[2], b[2]) - Math.max(a[0], b[0]), h = Math.min(a[3], b[3]) - Math.max(a[1], b[1]);
  if (w <= 0 || h <= 0) return 0;
  const inter = w * h;
  return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter);
};

// Đầu ra (1, 4 + nc, N): cx, cy, w, h rồi điểm từng lớp. Như Ultralytics: mỗi hộp lấy lớp điểm cao nhất, giữ hộp có điểm
// > minConf, NMS riêng từng lớp (IoU > iou thì bỏ), tối đa maxDet hộp; sau đó lọc theo ngưỡng riêng từng lớp (conf[lớp]).
export function postprocess(output, nc, { conf, iou: iouThres, maxDet }, maxNms = 30000) {
  const n = output.length / (4 + nc), minConf = Math.min(...conf);
  let cand = [];
  for (let a = 0; a < n; a++) {
    let best = -1, cls = 0;
    for (let c = 0; c < nc; c++) {
      const s = output[(4 + c) * n + a];
      if (s > best) { best = s; cls = c; }
    }
    if (!(best > minConf)) continue;
    const cx = output[a], cy = output[n + a], w = output[2 * n + a] / 2, h = output[3 * n + a] / 2;
    cand.push({ box: [cx - w, cy - h, cx + w, cy + h], score: best, cls });
  }
  cand.sort((p, q) => q.score - p.score);
  cand = cand.slice(0, maxNms);
  const keep = [];
  const removed = new Uint8Array(cand.length);
  for (let i = 0; i < cand.length && keep.length < maxDet; i++) {
    if (removed[i]) continue;
    keep.push(cand[i]);
    for (let j = i + 1; j < cand.length; j++) {
      if (!removed[j] && cand[j].cls === cand[i].cls && iou(cand[i].box, cand[j].box) > iouThres) removed[j] = 1;
    }
  }
  return keep.filter((d) => d.score >= conf[d.cls]);  // >= như eval_ood.py
}

// Hộp trên ảnh letterbox → tọa độ ảnh gốc, cắt theo biên ảnh (scale_boxes với padding = True)
export function scaleBoxes(dets, lb, width, height) {
  const clip = (v, hi) => Math.min(Math.max(v, 0), hi);
  return dets.map((d) => ({
    ...d,
    box: [clip((d.box[0] - lb.left) / lb.r, width), clip((d.box[1] - lb.top) / lb.r, height),
      clip((d.box[2] - lb.left) / lb.r, width), clip((d.box[3] - lb.top) / lb.r, height)],
  }));
}

// Chạy mô hình trên một ảnh/khung hình; ort là onnxruntime-web đã nạp, session tạo từ model.onnx
export async function detect(ort, session, cfg, source, width, height, canvas) {
  const { data, lb } = preprocess(source, width, height, cfg.imgsz, canvas);
  const input = new ort.Tensor("float32", data, [1, 3, cfg.imgsz, cfg.imgsz]);
  const out = await session.run({ [session.inputNames[0]]: input });
  const dets = postprocess(out[session.outputNames[0]].data, cfg.names.length, cfg);
  return scaleBoxes(dets, lb, width, height);
}
