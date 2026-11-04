// Lịch sử vi phạm lưu trong IndexedDB của máy (không có máy chủ). Mỗi bản ghi: thời điểm, nguồn, kích thước ảnh,
// danh sách người (hộp, độ tin cậy, có vi phạm), thời gian xử lý, ảnh JPEG và cờ đã xem.
const DB = "helmetcheck", STORE = "checks";

function open() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE, { keyPath: "id", autoIncrement: true });
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function tx(mode, fn) {
  const db = await open();
  return new Promise((resolve, reject) => {
    const t = db.transaction(STORE, mode), req = fn(t.objectStore(STORE));
    t.oncomplete = () => resolve(req?.result);
    t.onerror = t.onabort = () => reject(t.error);  // bị hủy mà không bắt thì promise treo mãi
  });
}

export const addCheck = (rec) => tx("readwrite", (s) => s.add({ ...rec, seen: false }));
export const listChecks = async () => ((await tx("readonly", (s) => s.getAll())) ?? []).sort((a, b) => b.id - a.id);
// Ghi lại bản ghi kèm chính Blob ảnh vừa đọc ra từ IndexedDB làm WebKit hỏng các Blob của ảnh đó trong phiên (màn chi tiết trống trên
// iPad, WebKitBlobResource error 1; tái hiện bằng Playwright WebKit, bỏ bước ghi thì hết) → ghi bản chép của ảnh, và nơi gọi dùng bản
// ghi đọc lại.
export const markSeen = async (id) => {
  const rec = await tx("readonly", (s) => s.get(id));
  if (!rec || rec.seen) return rec;
  const image = new Blob([await rec.image.arrayBuffer()], { type: rec.image.type });
  await tx("readwrite", (s) => s.put({ ...rec, image, seen: true }));
  return tx("readonly", (s) => s.get(id));
};
export const deleteCheck = (id) => tx("readwrite", (s) => s.delete(id));
export const clearChecks = () => tx("readwrite", (s) => s.clear());

// Khung hình hiện tại (ảnh hoặc video) → JPEG, cạnh dài tối đa 1280 px để lịch sử không quá nặng
export function snapshot(source, width, height, maxSide = 1280) {
  const k = Math.min(1, maxSide / Math.max(width, height));
  const c = document.createElement("canvas");
  c.width = Math.round(width * k);
  c.height = Math.round(height * k);
  c.getContext("2d").drawImage(source, 0, 0, c.width, c.height);
  return new Promise((resolve) => c.toBlob(resolve, "image/jpeg", 0.85));
}
