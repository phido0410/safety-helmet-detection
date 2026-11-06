// Xem chi tiết từng người vi phạm, chạy thật từ đầu tới cuối trên Chrome: phát video demo tới lúc app lưu ảnh, mở ảnh đó trong Lịch sử trên màn máy tính và
// màn điện thoại, so ảnh cắt đang hiện với khung đã lưu; thêm bản ghi 1 người và 5 người để xem bố cục. Không nằm trong npm test: cần Chrome và trang đang chạy.
//   node demo/test/zoom.mjs <url> <video.mp4> [thư mục lưu ảnh chụp, không commit vì có khung hình video]
import { spawn } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, resolve } from "node:path";
import { cropStyle, fitCrop, violators } from "../src/lib/crop.js";
const [url, videoArg, out] = process.argv.slice(2), video = resolve(videoArg);  // Chrome không mở được đường dẫn có ".."
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", ["--headless=new", "--remote-debugging-port=9362", "--ignore-certificate-errors", "--autoplay-policy=no-user-gesture-required",
  `--user-data-dir=${mkdtempSync(tmpdir() + "/cdpz")}`, "about:blank"], { stdio: "ignore" });
setTimeout(() => { console.log("hết giờ"); chrome.kill(); process.exit(2); }, 240000);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let target; for (let i = 0; i < 50 && !target; i++) { await sleep(200); try { target = (await (await fetch("http://127.0.0.1:9362/json")).json()).find((t) => t.type === "page"); } catch {} }
const ws = new WebSocket(target.webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r));
let id = 0, failed = 0; const pending = {}, errors = [];
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id) pending[d.id]?.(d); else if (d.method === "Runtime.exceptionThrown") errors.push(JSON.stringify(d.params.exceptionDetails).slice(0, 300)); };
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
const js = async (e) => (await send("Runtime.evaluate", { expression: e, awaitPromise: true, returnByValue: true })).result?.result?.value;
const until = async (e, ms = 90000) => { for (let t = 0; t < ms; t += 200) { if (await js(e)) return; await sleep(200); } throw new Error(`hết giờ: ${e}\n${errors.join("\n")}`); };
const check = (ok, msg) => { if (!ok) { failed++; console.log("SAI:", msg); } };
const shot = async (name) => { if (!out) return; await sleep(400); writeFileSync(`${out}/${name}.png`, Buffer.from((await send("Page.captureScreenshot", { format: "png" })).result.data, "base64")); };
const viewport = async (width, height, mobile) => {
  await send("Emulation.setTouchEmulationEnabled", { enabled: mobile, maxTouchPoints: mobile ? 5 : 0 });
  await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: mobile ? 2 : 1, mobile });
};
const clickText = (sel, re) => `[...document.querySelectorAll('${sel}')].find((b) => ${re}.test(b.innerText)).click()`;
const db = `new Promise((r, j) => { const q = indexedDB.open("helmetcheck", 1); q.onsuccess = () => r(q.result); q.onerror = j; })`;
const records = () => js(`(async () => { const d = await ${db}; const a = await new Promise((r) => { const q = d.transaction("checks").objectStore("checks").getAll(); q.onsuccess = () => r(q.result); });
  return a.map(({ image, ...x }) => ({ ...x, bytes: image.size })); })()`);
// so ảnh cắt đang hiện với khung đã lưu: đúng số người, đúng vùng cắt, không méo, ảnh tải được
const compare = async (rec, where) => {
  const shown = await js(`[...document.querySelectorAll('.zoomimg')].map((e) => { const c = getComputedStyle(e), a = e.getBoundingClientRect(), t = e.parentElement.getBoundingClientRect();
    return { size: c.backgroundSize, pos: c.backgroundPosition, blob: c.backgroundImage.startsWith('url("blob:'), w: a.width, h: a.height, inside: a.left >= t.left - 1 && a.right <= t.right + 1 && a.top >= t.top - 1 && a.bottom <= t.bottom + 1 }; })`);
  const bad = violators(rec.people);
  check(shown.length === bad.length, `${where}: ${shown.length} ô, ${bad.length} người vi phạm`);
  bad.forEach((p, i) => {
    const crop = fitCrop(p.box, rec.width, rec.height), want = cropStyle("u", rec.width, rec.height, crop), s = shown[i];
    const nums = (t) => t.split(" ").map(parseFloat), same = (a, b) => a.every((v, k) => Math.abs(v - b[k]) < 0.01);
    check(s.blob, `${where}, người ${i + 1}: ảnh nền không phải ảnh đã lưu`);
    check(same(nums(s.size), nums(want.backgroundSize)) && same(nums(s.pos), nums(want.backgroundPosition)), `${where}, người ${i + 1}: vùng cắt ${s.size} / ${s.pos}, phải là ${want.backgroundSize} / ${want.backgroundPosition}`);
    check(s.inside && Math.abs(s.w / s.h - crop[2] / crop[3]) < 0.02, `${where}, người ${i + 1}: ảnh cắt ${s.w}×${s.h} tràn ô hoặc méo (tỉ lệ phải là ${crop[2] / crop[3]})`);
  });
  return shown;
};
await send("Runtime.enable"); await send("Page.enable"); await send("DOM.enable");
console.log(`${basename(video)} trên ${url}, ${new Date().toISOString().slice(0, 10)}`);

// 1. Máy tính: phát video demo tới lúc app tự lưu ảnh
await viewport(1440, 900, false);
await send("Page.navigate", { url });
await until(`[...document.querySelectorAll('.segmented button')].some((b) => /^Video$/.test(b.innerText))`);
await until("!document.querySelector('.drophint')?.innerText.includes('Đang tải')");
await sleep(5000);
await js(clickText(".segmented button", "/^Video$/")); await sleep(300);
const { root } = (await send("DOM.getDocument", { depth: -1 })).result;
const { nodeId } = (await send("DOM.querySelector", { nodeId: root.nodeId, selector: "input[type=file][accept^=video]" })).result;
await send("DOM.setFileInputFiles", { nodeId, files: [video] });
await until(`[...document.querySelectorAll('.panel .btn')].some((b) => /Phát/.test(b.innerText))`);
await js(clickText(".panel .btn", "/Phát/"));
let recs = []; for (let t = 0; t < 40000 && !recs.length; t += 250) { recs = await records(); if (!recs.length) await sleep(250); }
check(recs.length > 0, "video demo không lưu ảnh nào");
await sleep(600); recs = await records();
const rec = recs[0];
console.log(`ảnh lưu ở giây ${rec.videoTime?.toFixed(1)}: ${violators(rec.people).length} vi phạm / ${rec.people.length} người, ${rec.width}×${rec.height}, ${Math.round(rec.bytes / 1024)} KB`);
await until("!!document.querySelector('.recent button')");
await js("document.querySelector('.recent button').click()");
await until("!!document.querySelector('.detail.wide .zoomimg')");
check(!(await js("[...document.querySelectorAll('.detail .btn')].some((b) => /Xem chi tiết/.test(b.innerText))")), "máy tính: không cần nút Xem chi tiết");
const onDesk = await compare(rec, "máy tính");
await shot("may_tinh");
console.log(`máy tính: ${onDesk.map((s) => `${Math.round(s.w)}×${Math.round(s.h)}`).join(", ")} px`);

// 2. Điện thoại: màn ảnh có nút, bấm mở màn chi tiết, quay lại vẫn còn ảnh
await viewport(414, 896, true);
await send("Page.reload"); await sleep(1000); await until("!!document.querySelector('.thumb')");
await js("document.querySelector('.thumb').click()"); await until("!!document.querySelector('.rowbtn .crop')");
await js("document.querySelector('.rowbtn').click()"); await until("!!document.querySelector('.detail img')");
const label = await js("[...document.querySelectorAll('.meta .btn')].map((b) => b.innerText).join()");
check(label === `Xem chi tiết ${violators(rec.people).length} người`, `điện thoại: nút ghi "${label}"`);
await shot("dien_thoai_anh");
await js(clickText(".meta .btn", "/Xem chi tiết/")); await until("!!document.querySelector('.zoomscreen .zoomimg')");
check((await js("document.activeElement.tagName")) === "H1", "mở màn chi tiết: tiêu điểm phải ở tiêu đề");
const onPhone = await compare(rec, "điện thoại");
await shot("dien_thoai_chi_tiet");
console.log(`điện thoại: ${onPhone.map((s) => `${Math.round(s.w)}×${Math.round(s.h)}`).join(", ")} px`);
await js(clickText(".navbar .link", "/Ảnh vi phạm/")); await until("!!document.querySelector('.detail img')");
await until("document.querySelector('.detail img').naturalWidth > 0", 5000);
check(/Xem chi tiết/.test(await js("document.activeElement.innerText")), "quay lại: tiêu điểm phải về nút Xem chi tiết");
check((await js("document.querySelector('.detail img').naturalWidth")) === rec.width, "quay lại: ảnh gốc không còn");

// 3. Điện thoại cầm ngang: nút không đẩy mất ảnh
await viewport(896, 414, true); await sleep(500);
const land = await js("(() => { const i = document.querySelector('.detail img').getBoundingClientRect(), b = [...document.querySelectorAll('.meta .btn')][0].getBoundingClientRect(); return { h: i.height, bottom: b.bottom, btn: b.height, screen: innerHeight }; })()");
check(land.h >= 250 && land.bottom <= land.screen && land.btn < 56, `cầm ngang: ảnh cao ${land.h}, nút cao ${land.btn}, tới ${land.bottom} / ${land.screen}`);
await shot("dien_thoai_ngang");
await js(clickText(".meta .btn", "/Xem chi tiết/")); await until("!!document.querySelector('.zoomscreen .zoomimg')");
const landTile = await js("document.querySelector('.zoomtile').getBoundingClientRect().height");
check(landTile > 300 && landTile <= 414 - 44, `cầm ngang: ô người cao ${landTile}, không thấy trọn một người trong màn`);
await compare(rec, "cầm ngang");
await shot("dien_thoai_ngang_chi_tiet");
await js(clickText(".navbar .link", "/Ảnh vi phạm/")); await until("!!document.querySelector('.detail img')");
console.log(`cầm ngang: ảnh cao ${Math.round(land.h)} px, ô người cao ${Math.round(landTile)} px`);
await viewport(414, 896, true);

// 4. Bố cục khi có 1 và 5 người vi phạm (bản ghi chép từ ảnh thật)
const addCopy = (people) => js(`(async () => { const d = await ${db}; const all = await new Promise((r) => { const q = d.transaction("checks").objectStore("checks").getAll(); q.onsuccess = () => r(q.result); }); const x = all[0];
  await new Promise((r, j) => { const t = d.transaction("checks", "readwrite"); const { id, ...rest } = x; t.objectStore("checks").add({ ...rest, people: ${JSON.stringify(people)} }); t.oncomplete = r; t.onerror = j; }); })()`);
const open = async () => { await send("Page.reload"); await sleep(1000); await until("!!document.querySelector('.thumb')"); await js("document.querySelector('.thumb').click()"); await until("!!document.querySelector('.rowbtn .crop')");
  await js("document.querySelector('.rowbtn').click()"); await until("!!document.querySelector('.detail img')"); await js(clickText(".meta .btn", "/Xem chi tiết/")); await until("!!document.querySelector('.zoomscreen .zoomimg')"); };
const first = violators(rec.people)[0];
await addCopy([first]); await open();
const one = await compare({ ...rec, people: [first] }, "1 người");
await shot("mot_nguoi");
console.log(`1 người: ${one.map((s) => `${Math.round(s.w)}×${Math.round(s.h)}`).join(", ")} px`);
// người ở gần camera (cảnh demo trực tiếp): ảnh phải chiếm phần lớn ô, không trống nhiều
const near = [{ ...first, n: 1, box: [80, 60, 620, 700], violation: true }, { ...first, n: 2, box: [680, 120, 1220, 700], violation: true }];
await addCopy(near); await open();
const close = await compare({ ...rec, people: near }, "người ở gần");
const fill = await js("[...document.querySelectorAll('.zoomimg')].map((e) => { const a = e.getBoundingClientRect(), t = e.parentElement.getBoundingClientRect(); return (a.width * a.height) / (t.width * t.height); })");
check(fill.every((v) => v > 0.8), `người ở gần: ảnh chỉ chiếm ${fill.map((v) => Math.round(v * 100)).join(", ")}% ô`);
await shot("nguoi_o_gan");
await viewport(896, 414, true); await sleep(500);
const nearLand = await js("(() => { const t = document.querySelector('.zoomtile').getBoundingClientRect(), i = document.querySelector('.zoomimg').getBoundingClientRect(); return { h: t.height, img: i.height }; })()");
check(nearLand.h > 300 && nearLand.h <= 414 - 44 && nearLand.img > 250, `cầm ngang, người ở gần: ô cao ${nearLand.h}, ảnh cao ${nearLand.img} (ô phải cao gần bằng màn, không thu nhỏ người)`);
await compare({ ...rec, people: near }, "cầm ngang, người ở gần");
await shot("nguoi_o_gan_ngang");
await viewport(414, 896, true); await sleep(300);
console.log(`người ở gần: ${close.map((s) => `${Math.round(s.w)}×${Math.round(s.h)}`).join(", ")} px`);
const five = [0, 1, 2, 3, 4].map((i) => ({ ...first, n: i + 1, box: [20 + i * 240, 100, 220 + i * 240, 700], violation: true }));
await addCopy(five); await open();
await compare({ ...rec, people: five }, "5 người");
check(await js("(() => { const e = document.querySelector('.zoomscreen'); return e.scrollHeight > e.clientHeight; })()"), "5 người: màn chi tiết phải cuộn được");
await shot("nam_nguoi");

check(errors.length === 0, `lỗi trên trang:\n${errors.join("\n")}`);
ws.close(); chrome.kill();
console.log(`zoom: ${failed ? `${failed} chỗ SAI` : "đạt"}`);
process.exit(failed ? 1 : 0);
