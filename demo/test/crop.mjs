// Phần xem chi tiết trong Lịch sử: vùng cắt vừa khung từng người vi phạm, CSS hiện đúng vùng đó, không méo ảnh.
import { cropStyle, fitCrop, fitIn, tileRatio, violators } from "../src/lib/crop.js";

let failed = 0;
const check = (ok, msg) => { if (!ok) { failed++; console.log("SAI:", msg); } };
const near = (a, b) => Math.abs(a - b) < 1e-6;
const W = 1280, H = 720;
let seed = 42;
const rand = (lo, hi) => { seed = (seed * 16807) % 2147483647; return lo + ((seed - 1) / 2147483646) * (hi - lo); };
const pct = (s) => s.split(" ").map((v) => parseFloat(v));

{  // giữa ảnh: chứa trọn khung, chừa lề 8% ngang, 4% dọc
  const [x, y, w, h] = fitCrop([500, 100, 700, 600], W, H);
  check(near(x, 484) && near(y, 80) && near(w, 232) && near(h, 540), `lề giữa ảnh: ${[x, y, w, h]}`);
}
{  // sát mép: lề bị cắt theo ảnh, không ra ngoài
  const a = fitCrop([0, 0, 100, 200], W, H), b = fitCrop([1200, 600, W, H], W, H);
  check(a[0] === 0 && a[1] === 0 && near(a[2], 108) && near(a[3], 208), `sát góc trên trái: ${a}`);
  check(near(b[0] + b[2], W) && near(b[1] + b[3], H), `sát góc dưới phải: ${b}`);
}
{  // khung tràn ra ngoài ảnh (số thực từ mô hình) hoặc bằng cả ảnh: vùng cắt là cả ảnh
  const c = fitCrop([-5, -5, W + 5, H + 5], W, H);
  check(c[0] === 0 && c[1] === 0 && c[2] === W && c[3] === H, `khung tràn ảnh: ${c}`);
  const s = cropStyle("u", W, H, c);
  check(s.backgroundSize === "100% 100%" && s.backgroundPosition === "0% 0%", `vùng cắt cả ảnh không được chia cho 0: ${s.backgroundSize} / ${s.backgroundPosition}`);
}
for (let k = 0; k < 300; k++) {  // CSS hiện đúng vùng cắt: tính ngược từ % ra pixel
  const x1 = rand(0, W - 40), y1 = rand(0, H - 40), box = [x1, y1, rand(x1 + 30, W), rand(y1 + 30, H)];
  const crop = fitCrop(box, W, H), s = cropStyle("u", W, H, crop);
  check(crop[0] <= box[0] && crop[1] <= box[1] && crop[0] + crop[2] >= box[2] && crop[1] + crop[3] >= box[3], `vùng cắt phải chứa trọn khung: ${box} → ${crop}`);
  check(crop[0] >= 0 && crop[1] >= 0 && crop[0] + crop[2] <= W + 1e-9 && crop[1] + crop[3] <= H + 1e-9, `vùng cắt ra ngoài ảnh: ${crop}`);
  const [sw, sh] = pct(s.backgroundSize), [px, py] = pct(s.backgroundPosition), w = (W * 100) / sw, h = (H * 100) / sh;
  check(near(w, crop[2]) && near(h, crop[3]), `cỡ nền sai: ${s.backgroundSize} ↔ ${crop}`);
  check((crop[2] >= W || near((px / 100) * (W - w), crop[0])) && (crop[3] >= H || near((py / 100) * (H - h), crop[1])), `vị trí nền sai: ${s.backgroundPosition} ↔ ${crop}`);
}
for (let k = 0; k < 300; k++) {  // nằm trọn trong ô và không méo, người cao lẫn người cúi ngang
  const ratio = rand(0.15, 3), tile = k % 2 ? 0.4 : 0.65, f = fitIn(ratio, tile), pw = parseFloat(f.width), ph = parseFloat(f.height);
  check(pw <= 100 + 1e-9 && ph <= 100 + 1e-9 && (near(pw, 100) || near(ph, 100)), `không vừa ô: ${ratio} trong ${tile}: ${f.width} ${f.height}`);
  check(near((pw * tile) / ph, ratio), `ảnh cắt bị méo: ${ratio} trong ${tile}: ${f.width} ${f.height}`);
}
{  // chỉ người vi phạm, từ trái sang phải; không ai vi phạm thì rỗng
  const people = [{ n: 1, box: [700, 0, 800, 9], violation: true }, { n: 2, box: [100, 0, 200, 9] }, { n: 3, box: [300, 0, 400, 9], violation: true }, { n: 4, box: [0, 0, 9, 9], far: true, violation: false }];
  check(violators(people).map((p) => p.n).join() === "3,1", `thứ tự người vi phạm: ${violators(people).map((p) => p.n)}`);
  check(violators([{ n: 1, box: [0, 0, 9, 9] }]).length === 0 && violators([]).length === 0, "không có người vi phạm");
  check(people[0].n === 1, "không được đổi thứ tự danh sách gốc");
}

{  // tỉ lệ ô theo dáng người: đứng thì ô cao, ở gần thì gần vuông, không có ô quá dẹt; ảnh chiếm phần lớn ô
  const crop = (r) => [0, 0, r * 100, 100], fill = (r, t) => { const f = fitIn(r, t); return (parseFloat(f.width) * parseFloat(f.height)) / 1e4; };
  check(near(tileRatio([crop(0.43), crop(0.37)]), 0.4), `2 người đứng: ${tileRatio([crop(0.43), crop(0.37)])}`);
  check(near(tileRatio([crop(0.9), crop(0.8)]), 0.85) && fill(0.8, 0.85) > 0.9, `2 người ở gần: ${tileRatio([crop(0.9), crop(0.8)])}`);
  check(near(tileRatio([crop(0.5), crop(0.9), crop(0.6)]), 0.6), `3 người: lấy trung vị: ${tileRatio([crop(0.5), crop(0.9), crop(0.6)])}`);
  check(near(tileRatio([crop(3), crop(3)]), 1) && near(tileRatio([crop(0.1), crop(0.1)]), 0.4), "nhiều người: tỉ lệ ô phải nằm trong 0,4–1");
  check(near(tileRatio([crop(0.43)]), 0.65) && near(tileRatio([crop(0.9)]), 0.9) && near(tileRatio([crop(3)]), 1.2), "một người: tỉ lệ ô theo người đó, trong 0,65–1,2");
}

console.log(`crop: 7 nhóm tình huống: ${failed ? `${failed} chỗ SAI` : "đạt"}`);
process.exit(failed ? 1 : 0);
