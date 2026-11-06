// Màn giới thiệu (markup và CSS ở index.html): đổi theo tiến độ tải mô hình thật, tải xong thì rời màn. Không phải thành phần React vì
// nó phải hiện trước khi JS tải xong và trước khi React chạy.
const NAME_MS = 780;      // tên HelmetCheck hiện xong (sp-rise: trễ 0,42 s + 0,36 s)
const HOLD_MS = 800;      // giữ tên trên màn thêm một nhịp rồi mới vào app (anh yêu cầu 0,5–1 s)
const BAR_MS = 1200;      // còn đang tải sau mốc này thì hiện thanh tiến độ
const STUCK_MS = 2500;    // đã tải xong (bộ nhớ đệm) mà khởi động mô hình lâu quá mốc này thì cũng hiện, để biết app vẫn đang làm việc
const CROSS_MS = 500;     // hai dải băng cắt chéo (sp-up-in + sp-down-in 0,37 s) và giữ một nhịp, rồi mới kéo lớp vàng đi
const WIPE_MS = 720;      // lớp vàng đã ra hết khỏi màn (sp-wipe 0,95 s, ~0,65 s cuối màn dọc, ~0,70 s màn gần vuông); phần còn lại không nhìn thấy
const FADE_MS = 260;      // bật Giảm chuyển động: chỉ mờ dần (sp-gone)
// Sọc và mũ vẫn chạy khi mạng đã đứng, nên màn tự nhìn không biết hỏng: lâu không có dữ liệu mới thì đưa lối thoát, vẫn tải tiếp
const STALL_MS = 20000;   // không nhận thêm dữ liệu
const BOOT_MS = 30000;    // đã tải xong, đang khởi động mô hình

const $ = (id) => document.getElementById(id);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
// chuyển động bắt đầu từ lúc trang vẽ lần đầu, không phải lúc điều hướng; mạng chậm thì hai mốc lệch nhau
const sincePaint = () => performance.now() - (performance.getEntriesByName("first-contentful-paint")[0]?.startTime ?? 0);
let leaving = false, shown = false, stalled = false, watchdog = 0, latest = -1;

function showBar() {
  if (shown || leaving || !$("splash")) return;
  shown = true;
  $("splash").classList.add("slow");
}
setTimeout(showBar, STUCK_MS);

function showExit(title, why, detail) {
  const el = $("splash");
  if (!el || leaving) return;
  el.classList.add("fail");
  $("sp-title").textContent = title;
  $("sp-why").textContent = why;
  $("sp-detail").textContent = detail ?? "";
  $("sp-fail").hidden = false;
  $("sp-retry").onclick = () => location.reload();
  $("sp-skip").onclick = () => leave(true);
  $("sp-retry").focus();
}
function hideExit() {
  const had = $("sp-fail").contains(document.activeElement);
  $("splash").classList.remove("fail");
  $("sp-fail").hidden = true;
  if (had) $("sp-rail").focus();  // nút vừa giữ tiêu điểm biến mất: đưa về thanh tiến độ, không để rơi về body
}

function watch(ms) {
  clearTimeout(watchdog);
  watchdog = setTimeout(() => {
    stalled = true;
    if (latest < 1) showExit("Mô hình tải lâu hơn bình thường", "Mạng có thể đang yếu. App vẫn đang tải tiếp.");
    else showExit("Mô hình khởi động lâu hơn bình thường", "Máy có thể đang thiếu bộ nhớ. App vẫn đang thử tiếp.");
  }, ms);
}
watch(STALL_MS);

export function splashProgress(p) {
  if (!$("splash") || leaving || p === latest) return;
  latest = p;
  const pct = Math.round(p * 100);
  $("sp-fill").style.transform = `translateX(${pct - 100}%)`;
  $("sp-rail").setAttribute("aria-valuenow", pct);
  $("sp-pct").textContent = p < 1 ? `${pct}%` : "";
  $("sp-text").textContent = p < 1 ? "Đang tải mô hình" : "Đang khởi động mô hình";  // tải xong còn phải biên dịch mô hình, % đứng yên ở đây
  if (p < 1 && sincePaint() > BAR_MS) showBar();
  if (stalled) { stalled = false; hideExit(); }  // dữ liệu chạy lại
  watch(p < 1 ? STALL_MS : BOOT_MS);
}

// quick: người dùng bấm Vào app, không có nhịp băng cắt chéo
async function leave(quick) {
  const el = $("splash");
  if (!el || leaving) return;
  leaving = true;
  clearTimeout(watchdog);
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!quick) {
    hideExit();
    await sleep((calm ? 0 : NAME_MS) + HOLD_MS - sincePaint());
  }
  if (!calm && !quick) {
    if (shown) {  // chỉ lần tải lâu mới có nhịp băng cắt chéo; mở lại từ bộ nhớ đệm thì vào thẳng
      el.classList.add("done");
      await sleep(CROSS_MS);
    }
  }
  $("root").inert = false;
  document.querySelector('meta[name="theme-color"]').content = "#000000";
  el.classList.add("out");
  await sleep(calm ? FADE_MS : WIPE_MS);
  el.remove();
}
export const splashDone = () => leave(false);

// Lỗi thật: dừng ở màn này, nói rõ lý do. "Vào app" để vẫn xem được Lịch sử đã lưu khi không có mô hình.
export function splashFail(why, detail) {
  clearTimeout(watchdog);
  showExit("Chưa tải được mô hình", why, detail);
}
