// Camera trực tiếp khi điện thoại cầm ngang mà giao diện không xoay theo (khóa xoay dọc): khung hình vẫn dọc nhưng cảnh nằm ngang, và
// mô hình (chỉ học ảnh người đứng) gần như không nhận ra mũ (OOD-4 xoay 90°: 165 → 6–13 dự đoán "có mũ"). Đọc hướng cầm máy từ cảm
// biến (deviceorientation: beta, gamma), trừ hướng giao diện, rồi xoay khung về thẳng đứng trước khi đưa vào mô hình; khung khoanh
// được xoay ngược về khung gốc để vẽ và theo dõi; ảnh lưu là khung đã xoay thẳng (xem lại trong Lịch sử thì người đứng thẳng).

// Góc của hướng "lên" so với cạnh trên máy (độ, 0..360; 90 = đầu máy quay sang trái), theo công thức vector "lên" từ beta, gamma của
// đặc tả DeviceOrientation. null khi máy nằm gần phẳng (không xác định được hướng): giữ hướng cũ.
export function upAngle(beta, gamma) {
  const b = (beta * Math.PI) / 180, g = (gamma * Math.PI) / 180;
  const x = -Math.cos(b) * Math.sin(g), y = Math.sin(b);
  if (Math.hypot(x, y) < 0.5) return null;
  return ((Math.atan2(x, y) * 180) / Math.PI + 360) % 360;
}

// Làm tròn về 0 / 90 / 180 / 270, chỉ đổi khi góc đã vào hẳn góc phần tư mới (cách tâm < 30°), tránh nhảy qua lại quanh 45°
export function quadrant(angle, prev) {
  const q = (Math.round(angle / 90) * 90) % 360, d = Math.abs(((angle - q + 540) % 360) - 180);
  return d < 30 ? q : prev;
}

// Góc phải xoay khung (theo chiều kim đồng hồ) để cảnh thẳng đứng. Camera sau: cảnh xoay ngược chiều máy; camera trước (khung không
// lật gương) thì cùng chiều.
// shortcut: thử trên iPhone 11 Pro Max, camera trước cầm ngang vẫn bị lật; sửa khi cần dùng camera trước.
export function frameRotation(deviceQ, screenAngle, facing) {
  const rel = (((deviceQ - screenAngle) % 360) + 360) % 360;
  return facing === "user" ? rel : (360 - rel) % 360;
}

// Ma trận [a, b, c, d, e, f] của ctx.setTransform: vẽ khung W×H xoay rot độ theo chiều kim đồng hồ vào canvas đã đổi chiều
export function rotationMatrix(rot, W, H) {
  if (rot === 90) return [0, 1, -1, 0, H, 0];
  if (rot === 180) return [-1, 0, 0, -1, W, H];
  if (rot === 270) return [0, -1, 1, 0, 0, W];
  return [1, 0, 0, 1, 0, 0];
}

// Khung [x1, y1, x2, y2] trên khung hình gốc → khung trên canvas đã xoay (ảnh lưu thẳng đứng)
export function rotateBox([x1, y1, x2, y2], rot, W, H) {
  const [a, b, c, d, e, f] = rotationMatrix(rot, W, H);
  const [p, q] = [[x1, y1], [x2, y2]].map(([x, y]) => [a * x + c * y + e, b * x + d * y + f]);
  return [Math.min(p[0], q[0]), Math.min(p[1], q[1]), Math.max(p[0], q[0]), Math.max(p[1], q[1])];
}

// Khung [x1, y1, x2, y2] trên canvas đã xoay → khung trên khung hình gốc (nghịch đảo của rotationMatrix)
export function unrotateBox([x1, y1, x2, y2], rot, W, H) {
  const [a, b, c, d, e, f] = rotationMatrix(rot, W, H), det = a * d - b * c;
  const back = ([u, v]) => [(d * (u - e) - c * (v - f)) / det, (a * (v - f) - b * (u - e)) / det];
  const [p, q] = [back([x1, y1]), back([x2, y2])];
  return [Math.min(p[0], q[0]), Math.min(p[1], q[1]), Math.max(p[0], q[0]), Math.max(p[1], q[1])];
}

// Hướng nhìn của camera (vector đơn vị theo trục z của máy, công thức ma trận Z-X'-Y'' của đặc tả DeviceOrientation) và góc giữa hai
// hướng (độ). Camera trước nhìn ngược trục z nên góc giữa hai lần đo vẫn như camera sau.
export function viewDir(alpha, beta, gamma) {
  const [a, b, g] = [alpha, beta, gamma].map((d) => (d * Math.PI) / 180);
  return [Math.cos(a) * Math.sin(g) + Math.sin(a) * Math.sin(b) * Math.cos(g), Math.sin(a) * Math.sin(g) - Math.cos(a) * Math.sin(b) * Math.cos(g),
    Math.cos(b) * Math.cos(g)];
}
export const viewAngle = (u, v) => (Math.acos(Math.max(-1, Math.min(1, u[0] * v[0] + u[1] * v[1] + u[2] * v[2]))) * 180) / Math.PI;

const screenAngle = () => (typeof window.orientation === "number" ? window.orientation : screen.orientation?.angle ?? 0);

// Theo dõi hướng cầm máy; phải gọi ngay trong thao tác bấm của người dùng vì iOS hỏi quyền "Chuyển động và hướng" lúc đó.
// get(facing) trả góc xoay khung hiện tại; không có cảm biến hoặc bị từ chối quyền thì luôn 0 (như trước). view() trả hướng camera
// (viewDir) cho tracker, chưa có số đo thì null.
export function watchOrientation() {
  let q = 0, on = null, dir = null;
  const handle = (e) => {
    const a = e.beta == null ? null : upAngle(e.beta, e.gamma);
    if (a != null) q = quadrant(a, q);
    if (e.alpha != null && e.beta != null) dir = viewDir(e.alpha, e.beta, e.gamma);
  };
  const ask = globalThis.DeviceOrientationEvent?.requestPermission;
  (ask ? ask.call(DeviceOrientationEvent) : Promise.resolve("granted")).then((s) => {
    if (s === "granted") { on = handle; window.addEventListener("deviceorientation", on); }
  }, () => {});
  return { get: (facing) => frameRotation(q, screenAngle(), facing), view: () => dir, stop: () => on && window.removeEventListener("deviceorientation", on) };
}
