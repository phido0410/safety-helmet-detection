// Kiểm tra chọn số luồng WASM (src/lib/model.js): Safari 26.2 treo khi chạy đa luồng nên phải chạy một luồng; Safari mới chạy
// đa luồng; trình duyệt từng bị treo lần trước (dấu còn lại, cùng user agent, chưa quá 1 ngày) thì chạy một luồng, đổi phiên bản
// hoặc dấu đã cũ thì thử lại (iPhone 11: dấu kẹt do rời trang lúc đang chạy thử, ứng dụng chạy một luồng mãi, chậm gấp đôi).
import { OOM_MESSAGE, pickBackend, retryOom, singleThread } from "../src/lib/model.js";

const safari = (v) => `Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/${v} Mobile/15E148 Safari/604.1`;
const NOW = Date.parse("2026-11-04T20:00:00+07:00");
const mark = (ua, hoursAgo) => `${NOW - hoursAgo * 3600e3}|${ua}`;  // dấu ghi trước khi chạy thử đa luồng
const chrome = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36";
const cases = [
  [safari("26.2"), null, true, "Safari 26.2 (iPhone 17 của Nam, treo)"],
  [safari("26.4.1"), null, true, "Safari 26.4.1"],
  [safari("26.6.3"), null, false, "Safari 26.6.3 (iPhone 11, chạy tốt)"],
  [chrome, null, false, "Chrome máy tính"],
  [safari("26.6.3"), mark(safari("26.6.3"), 1), true, "lần trước treo (1 giờ trước), cùng trình duyệt"],
  [safari("26.7"), mark(safari("26.6.3"), 1), false, "lần trước treo nhưng đã cập nhật trình duyệt"],
  [safari("26.6.3"), mark(safari("26.6.3"), 25), false, "dấu treo đã quá 1 ngày: thử lại đa luồng"],
  [safari("26.6.3"), safari("26.6.3"), false, "dấu kiểu cũ (không có thời điểm, từng kẹt trên iPhone 11): thử lại đa luồng"],
];
let failed = 0;
for (const [ua, hung, want, name] of cases) {
  if (singleThread(ua, hung, NOW) !== want) { failed++; console.log(`SAI: ${name}: phải ${want ? "một luồng" : "đa luồng"}`); }
}
// Chọn WASM hay WebGPU theo số đo trên chính máy (Safari không cho biết đời máy: iPhone 11 và 17 cùng ghi "iPhone OS 18_7", 4 nhân).
// Số đo bench.html ở cỡ 800: iPhone 17 WASM 1 luồng 206 ms / WebGPU 54 ms; iPhone 11 WASM 229 / WebGPU 253. Chỉ chuyển khi WebGPU nhanh
// rõ (dưới 80% thời gian WASM), tránh đổi qua lại vì sai số đo.
const picks = [[206, 54, "webgpu", "iPhone 17"], [229, 253, "wasm", "iPhone 11"], [229, 200, "wasm", "WebGPU nhanh hơn chưa tới 20%"], [160, 50, "webgpu", "Chrome máy Mac"]];
for (const [w, g, want, name] of picks) if (pickBackend(w, g) !== want) { failed++; console.log(`SAI: ${name}: WASM ${w} ms, WebGPU ${g} ms phải chọn ${want}`); }
// Khởi tạo lỗi "Out of memory" (iPhone 17, tải lại ngay sau khi trang bị tắt): thử lại đúng một lần bằng bản nạp mới; lỗi khác không thử lại
const oom = new RangeError("Out of memory"), other = new Error("no available backend found");
const attempt = (errors) => { const tags = []; return { tags, open: async (tag) => { tags.push(tag); const e = errors.shift(); if (e) throw e; return "ok"; } }; };
const retries = [
  ["hết bộ nhớ một lần rồi được", [oom], "ok", ",?retry=1"],
  ["hết bộ nhớ hai lần", [oom, oom], OOM_MESSAGE, ",?retry=1"],
  ["lỗi khác không thử lại", [other], other.message, ""],
  ["không lỗi", [], "ok", ""],
];
for (const [name, errors, want, tags] of retries) {
  const a = attempt([...errors]), got = await retryOom(a.open, 0).catch((e) => e.message);
  if (got !== want || a.tags.join() !== tags) { failed++; console.log(`SAI: ${name}: ${got} (lần thử: ${a.tags.join()})`); }
}
console.log(`threads: ${cases.length + picks.length + retries.length} trường hợp: ${failed ? `${failed} chỗ SAI` : "đạt"}`);
process.exit(failed ? 1 : 0);
