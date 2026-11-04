// Kiểm tra xoay khung theo hướng cầm máy (src/lib/orientation.js): hướng "lên" từ beta/gamma, làm tròn có trễ, góc xoay khung cho
// camera sau / trước khi giao diện bị khóa dọc hoặc xoay theo, và khung khoanh xoay ngược đúng về khung hình gốc.
//   node demo/test/orientation.mjs
import { quadrant, frameRotation, rotationMatrix, unrotateBox, upAngle } from "../src/lib/orientation.js";

let failed = 0;
const check = (ok, msg) => { if (!ok) { failed++; console.log("SAI:", msg); } };
const near = (a, b) => a != null && Math.abs(((a - b + 540) % 360) - 180) < 1;

// cầm dọc; đầu máy quay sang trái (beta 0, gamma −90); sang phải; lộn ngược; nằm phẳng trên bàn
check(near(upAngle(90, 0), 0) && near(upAngle(0, -90), 90) && near(upAngle(0, 90), 270) && near(upAngle(-90, 0), 180) && upAngle(0, 0) === null,
  `upAngle: ${[upAngle(90, 0), upAngle(0, -90), upAngle(0, 90), upAngle(-90, 0), upAngle(0, 0)]}`);
// 40° vẫn là dọc (chưa vào hẳn góc phần tư ngang), 70° thì sang ngang; quay lại 50° vẫn giữ ngang
check(quadrant(40, 0) === 0 && quadrant(70, 0) === 90 && quadrant(50, 90) === 90 && quadrant(355, 90) === 0, "quadrant: trễ khi đổi hướng");

// khóa xoay dọc (giao diện 0°), đầu máy quay sang trái: camera sau phải xoay khung ngược chiều kim đồng hồ (270), camera trước 90;
// tắt khóa xoay (giao diện cũng xoay 90°): khung đã thẳng, không xoay
check(frameRotation(90, 0, "environment") === 270 && frameRotation(90, 0, "user") === 90 && frameRotation(270, 0, "environment") === 90
  && frameRotation(90, 90, "environment") === 0 && frameRotation(0, 0, "environment") === 0, "frameRotation");

// Khung khoanh trên canvas đã xoay → khung gốc: đưa 4 góc khung gốc qua đúng ma trận dùng để vẽ, lấy khung bao, rồi xoay ngược phải
// ra lại khung gốc; và một ví dụ cụ thể: xoay 90°, góc trên trái của khung gốc 1280×720 nằm ở góc trên phải của canvas 720×1280
const W = 1280, H = 720, box = [100, 50, 300, 650];
for (const rot of [0, 90, 180, 270]) {
  const [a, b, c, d, e, f] = rotationMatrix(rot, W, H);
  const pts = [[box[0], box[1]], [box[2], box[1]], [box[0], box[3]], [box[2], box[3]]].map(([x, y]) => [a * x + c * y + e, b * x + d * y + f]);
  const rbox = [Math.min(...pts.map((p) => p[0])), Math.min(...pts.map((p) => p[1])), Math.max(...pts.map((p) => p[0])), Math.max(...pts.map((p) => p[1]))];
  const back = unrotateBox(rbox, rot, W, H);
  check(back.every((v, i) => Math.abs(v - box[i]) < 1e-9), `xoay ${rot}°: ${box} → ${rbox} → ${back}`);
}
{
  const [a, b, c, d, e, f] = rotationMatrix(90, W, H);
  check(a * 0 + c * 0 + e === H && b * 0 + d * 0 + f === 0, "xoay 90°: góc trên trái phải sang góc trên phải");
}

console.log(`orientation: 8 trường hợp: ${failed ? `${failed} chỗ SAI` : "đạt"}`);
process.exit(failed ? 1 : 0);
