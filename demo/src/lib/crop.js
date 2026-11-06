// Xem chi tiết trong Lịch sử: cắt từng người vi phạm từ ảnh đã lưu, chỉ tính toán trên ảnh và tọa độ khung của bản ghi.
const MARGIN_X = 0.08, MARGIN_Y = 0.04;  // lề quanh khung để không cụt đầu, tay; không vượt ra ngoài ảnh

export const violators = (people) => people.filter((p) => p.violation).sort((a, b) => a.box[0] - b.box[0]);

export function fitCrop([x1, y1, x2, y2], width, height) {
  const mx = (x2 - x1) * MARGIN_X, my = (y2 - y1) * MARGIN_Y;
  const x = Math.max(0, x1 - mx), y = Math.max(0, y1 - my);
  return [x, y, Math.min(width, x2 + mx) - x, Math.min(height, y2 + my) - y];
}

// Tỉ lệ ô chung của một ảnh theo dáng người trong ảnh: người đứng ô cao, người ở gần ô gần vuông, để ô không trống nhiều mà các hàng vẫn đều
const TILE_MIN = 0.4, TILE_MAX = 1, ONE_MIN = 0.65, ONE_MAX = 1.2;
const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi);
export function tileRatio(crops) {
  const r = crops.map(([, , w, h]) => w / h).sort((a, b) => a - b), mid = r.length >> 1;
  if (r.length === 1) return clamp(r[0], ONE_MIN, ONE_MAX);
  return clamp(r.length % 2 ? r[mid] : (r[mid - 1] + r[mid]) / 2, TILE_MIN, TILE_MAX);
}

// Hiện vùng [x, y, w, h] của ảnh bằng background; vùng rộng bằng cả ảnh thì không còn chỗ để dời
export const cropStyle = (url, width, height, [x, y, w, h]) => ({
  backgroundImage: `url(${url})`,
  backgroundSize: `${(width / w) * 100}% ${(height / h) * 100}%`,
  backgroundPosition: `${w < width ? (x / (width - w)) * 100 : 0}% ${h < height ? (y / (height - h)) * 100 : 0}%`,
});

// Ảnh tỉ lệ ratio (rộng / cao) nằm trọn trong ô tỉ lệ tile, không méo; % theo cỡ của ô
export const fitIn = (ratio, tile) => (ratio > tile
  ? { width: "100%", height: `${(tile / ratio) * 100}%` }
  : { width: `${(ratio / tile) * 100}%`, height: "100%" });
