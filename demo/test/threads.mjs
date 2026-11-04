// Kiểm tra chọn số luồng WASM (src/lib/model.js): Safari 26.2 treo khi chạy đa luồng nên phải chạy một luồng; Safari mới chạy
// đa luồng; trình duyệt từng bị treo lần trước (dấu còn lại, cùng user agent) thì chạy một luồng, đổi phiên bản thì thử lại.
import { singleThread } from "../src/lib/model.js";

const safari = (v) => `Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/${v} Mobile/15E148 Safari/604.1`;
const chrome = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36";
const cases = [
  [safari("26.2"), null, true, "Safari 26.2 (iPhone 17 của Nam, treo)"],
  [safari("26.4.1"), null, true, "Safari 26.4.1"],
  [safari("26.6.3"), null, false, "Safari 26.6.3 (iPhone 11, chạy tốt)"],
  [chrome, null, false, "Chrome máy tính"],
  [safari("26.6.3"), safari("26.6.3"), true, "lần trước treo, cùng trình duyệt"],
  [safari("26.7"), safari("26.6.3"), false, "lần trước treo nhưng đã cập nhật trình duyệt"],
];
let failed = 0;
for (const [ua, hung, want, name] of cases) {
  if (singleThread(ua, hung) !== want) { failed++; console.log(`SAI: ${name}: phải ${want ? "một luồng" : "đa luồng"}`); }
}
console.log(`threads: ${cases.length} trường hợp: ${failed ? `${failed} chỗ SAI` : "đạt"}`);
process.exit(failed ? 1 : 0);
