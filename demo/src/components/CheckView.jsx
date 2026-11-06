import { useEffect, useRef, useState } from "react";
import Stage, { Capsule, verdictOf, peopleCount } from "./Stage.jsx";
import Crop, { CropView } from "./Crop.jsx";
import { IconAlert, IconCamera, IconCheck, IconClose, IconFlip, IconInfo, IconPause, IconPerson, IconPhoto, IconPlay, IconStack, IconStop,
  IconTimer, IconCompass, IconUpload, IconVideo } from "./Icons.jsx";
import { people as peopleOf } from "../lib/model.js";
import { addCheck, snapshot } from "../lib/history.js";
import { CONFIRM_MS, VIEW_DEG, createTracker } from "../lib/tracker.js";
import { rotateBox, rotationMatrix, unrotateBox, viewAngle, watchOrientation } from "../lib/orientation.js";
import { useWide } from "../lib/wide.js";

const CAPTURE_EVERY_MS = 3000;  // video/camera: hai ảnh cách nhau ít nhất 3 giây, chặn chụp liên tục khi tracker mất dấu (camera rung)
const FRAME_MAX_SIDE = 1280;    // khung hình được chép ra canvas cỡ này: vừa để phân tích, vừa là ảnh lưu
const camera = (facing) => ({ video: { facingMode: facing, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
// Máy không có màn cảm ứng (máy tính) chỉ có Ảnh, Video; iPhone, iPad có thêm Trực tiếp. Nhận theo khả năng, không theo tên trình
// duyệt (Safari trên iPad tự xưng là Mac).
const DESKTOP = navigator.maxTouchPoints === 0;
const MODES = [["photo", "Ảnh"], ["video", "Video"], ["live", "Trực tiếp"]].filter(([id]) => !DESKTOP || id !== "live");
const ms = (v) => (v ? `${Math.round(v)} ms` : "–");
const fps = (v) => (v ? `${v.toFixed(1).replace(".", ",")} khung/s` : "–");
// Thông số trên màn hình chính (thanh dưới khung ngắm; ô số ở bảng bên phải màn rộng): số người, lệch hướng camera so với ảnh vừa
// lưu (chỉ camera trực tiếp: turn là undefined ở ảnh, video; null khi chưa lưu ảnh hoặc không có cảm biến), thời gian xử lý một khung
const METRIC_ICONS = { person: IconPerson, turn: IconCompass, timer: IconTimer };
const deg = (v) => (v == null ? "–" : `${Math.round(v)}°`);
function metricsOf(people, took, turn, timeLabel = "ms mỗi khung") {
  const far = people.filter((p) => p.far).length;
  return [{ icon: "person", text: `${people.length - far} người${far ? ` +${far} xa` : ""}`, value: String(people.length - far), label: far ? `người (+${far} ở xa)` : "người" },
    ...(turn === undefined ? [] : [{ icon: "turn", text: `Lệch ${deg(turn)}`, value: deg(turn), label: "lệch hướng" }]),
    { icon: "timer", text: ms(took), value: took ? String(Math.round(took)) : "–", label: timeLabel }];  // ô hẹp: đơn vị sang nhãn
}
const pct = (s) => `${Math.round(s * 100)}%`;
const baseStats = (model) => [["Mô hình", model.name ?? "–"], ["Chạy trên", model.backend ?? "–"]];
const ruleNote = `Mỗi người không đội mũ chỉ được lưu một lần, sau khi bị báo vi phạm kéo dài khoảng ${CONFIRM_MS / 1000} giây; hai ảnh cách nhau ít nhất ${CAPTURE_EVERY_MS / 1000} giây. Camera trực tiếp: lia máy lệch quá ${VIEW_DEG}° so với lúc lưu ảnh gần nhất là cảnh mới, người ở cảnh mới vẫn được lưu.`;
const PASTE_KEY = /Mac|iPhone|iPad/.test(navigator.userAgent) ? "⌘V" : "Ctrl+V";
const FORMATS = "Ảnh JPG, PNG, WebP · video MP4, WebM";  // định dạng mọi trình duyệt đều mở được (HEIC, MOV chỉ Safari)
const BAD_FILE = "Không mở được tệp này. Hãy dùng ảnh JPG, PNG hoặc video MP4.";
const SAVE_FAILED = "Không lưu được ảnh vào lịch sử trên trình duyệt này (chế độ duyệt riêng tư?).";
const fileKind = (f) => (f?.type.startsWith("image/") ? "photo" : f?.type.startsWith("video/") ? "video" : null);

// Màn chính như app Camera: khung ngắm, kết luận nổi ở trên; màn hẹp có hàng chế độ và nút tròn ở dưới, màn rộng có bảng bên phải.
// Đổi chế độ là gắn lại component của chế độ đó (camera tắt, video dừng, tracker mới). Ảnh / video kéo thả hoặc dán vào trang thì
// chuyển sang đúng chế độ rồi được chế độ đó nhận (dropped).
export default function CheckView({ model, active, recent, onSaved, onHistory }) {
  const [mode, setMode] = useState(DESKTOP ? "photo" : "live");
  const [dropped, setDropped] = useState(null);  // { file, kind }
  const [dragging, setDragging] = useState(false);
  const [notice, setNotice] = useState(null);  // lỗi ngắn (tệp không mở được), tự ẩn sau 5 giây
  const wide = useWide();
  useEffect(() => { if (notice) { const t = setTimeout(() => setNotice(null), 5000); return () => clearTimeout(t); } }, [notice]);
  const take = (file) => {
    const kind = fileKind(file);
    if (!kind) return setNotice(BAD_FILE);
    setNotice(null);
    setMode(kind);
    setDropped({ file, kind });
  };
  useEffect(() => {
    if (!active) return;
    const paste = (e) => { const f = e.clipboardData?.files?.[0]; if (fileKind(f)) { e.preventDefault(); take(f); } };
    document.addEventListener("paste", paste);
    return () => document.removeEventListener("paste", paste);
  }, [active]);

  const props = { model, active, onSaved, dropped, consume: () => setDropped(null),
    chrome: { mode, setMode, recent, onHistory, model, wide, dragging, notice, notify: setNotice } };
  return (
    <div className="dropzone"
      onDragOver={(e) => { if (e.dataTransfer.types.includes("Files")) { e.preventDefault(); setDragging(true); } }}
      onDragLeave={(e) => !e.currentTarget.contains(e.relatedTarget) && setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); take(e.dataTransfer.files[0]); }}>
      {mode === "photo" ? <PhotoMode key="photo" {...props} /> : mode === "video" ? <VideoMode key="video" {...props} />
        : <LiveMode key="live" {...props} />}
    </div>
  );
}

// Khung chung của ba chế độ. Mỗi chế độ đưa vào: media, người phát hiện, kết luận, dòng tóm tắt, nút chính (shutter), nút phụ.
function Screen({ chrome, media, people = [], live, verdict, title, metrics, hint, shutter, secondary, stats, rule, cropSrc }) {
  const { mode, setMode, recent, onHistory, model, wide, dragging, notice } = chrome;
  const [info, setInfo] = useState(false);
  const [focus, setFocus] = useState(null);
  const status = model.status === "error" ? `Không tải được mô hình: ${model.error}`
    : model.status !== "ready" ? `Đang tải mô hình ${Math.round(model.progress * 100)}%` : null;
  const dropUI = DESKTOP && !media && mode !== "live";
  const openInfo = () => setInfo(true);
  return (
    <div className={`cam${wide ? " wide" : ""}`}>
      <div className={`viewfinder${dragging ? " dragging" : ""}`}>
        {media && <Stage width={media.width} height={media.height} people={people} live={live} focus={focus} onFocus={setFocus}>{media.node}</Stage>}
        {dropUI && <button type="button" className="drophint" onClick={shutter.onPress}>
          <span className="dropicon"><IconUpload size={34} /></span>
          <b>Kéo thả ảnh hoặc video công trường vào đây</b>
          <span>{status ?? `${FORMATS} · hoặc bấm để\u00a0chọn tệp · mô hình chạy ngay trên máy, không gửi đi đâu`}</span>
        </button>}
        {!dropUI && (status || hint) && <p className="hint">{status ?? hint}</p>}
        {notice && <p className="notice" role="alert">{notice}</p>}
        <div className="topbar">
          <span className="spacer" />
          {verdict && <Capsule {...verdict} />}
          {wide ? <span className="spacer" />
            : <button type="button" className="glass" aria-label="Thông tin" onClick={openInfo}><IconInfo /></button>}
        </div>
        {!wide && metrics && <p className="metrics">{metrics.map(({ icon, text }) => { const I = METRIC_ICONS[icon]; return <span key={icon}><I size={17} /><span>{text}</span></span>; })}</p>}
      </div>
      {wide ? <WidePanel {...{ chrome, people, verdict, title, metrics, hint, shutter, secondary, cropSrc, focus, setFocus, openInfo, hasMedia: !!media }} />
        : <div className="controls">
          <ModeRow mode={mode} setMode={setMode} />
          <div className="row">
            <button type="button" className="thumb" onClick={() => onHistory()}
              aria-label={`Lịch sử vi phạm${recent.unseen ? `, ${recent.unseen} mới` : ""}`}>
              {recent.rec ? <Crop key={recent.rec.id} rec={recent.rec} /> : <IconStack />}
              {recent.unseen > 0 && <span className="count">{recent.unseen}</span>}
            </button>
            <button type="button" className={`shutter ${shutter.kind}`} aria-label={shutter.label} onClick={shutter.onPress}
              disabled={shutter.disabled}><i /></button>
            {secondary ? <button type="button" className="round" aria-label={secondary.label} onClick={secondary.onPress}>
              {secondary.icon === "flip" ? <IconFlip size={26} /> : <IconClose size={26} />}</button>
              : <span className="spacer" />}
          </div>
        </div>}
      {info && <InfoSheet stats={stats} rule={rule} onClose={() => setInfo(false)} />}
    </div>
  );
}

const ModeRow = ({ mode, setMode }) => (
  <div className="modes">
    {MODES.map(([id, label]) => <button key={id} type="button" aria-pressed={mode === id} onClick={() => setMode(id)}>{label}</button>)}
  </div>
);

const BUTTON_ICONS = { photo: IconPhoto, video: IconVideo, flip: IconFlip, close: IconClose, play: IconPlay, pause: IconPause,
  camera: IconCamera, stop: IconStop };
const LIST_MAX = 5;  // bảng bên phải chỉ liệt kê 5 người vi phạm tin cậy nhất, còn lại gộp một dòng (camera đông người không nhảy dài)

// Bảng bên phải của màn rộng (máy tính, iPad ngang): kết luận, nút, danh sách người (chọn để làm nổi khung), lịch sử gần đây
// Ảnh cắt một người từ khung hình vừa phân tích (video / camera), vẽ lại mỗi khi có khung mới
function FrameCrop({ canvas, box, t }) {
  const ref = useRef();
  useEffect(() => {
    const c = ref.current, [x1, y1, x2, y2] = box, w = x2 - x1, h = y2 - y1;
    const side = Math.min(Math.max(w, h) * 1.15, canvas.width, canvas.height);
    const sx = Math.min(Math.max((x1 + x2) / 2 - side / 2, 0), canvas.width - side), sy = Math.min(Math.max(y1 - h * 0.05, 0), canvas.height - side);
    c.getContext("2d").drawImage(canvas, sx, sy, side, side, 0, 0, c.width, c.height);
  }, [canvas, box, t]);
  return <canvas ref={ref} width={80} height={80} className="crop" />;
}

function WidePanel({ chrome, people, verdict, title, metrics, hint, shutter, secondary, cropSrc, focus, setFocus, openInfo, hasMedia }) {
  const { mode, setMode, recent, onHistory } = chrome;
  // thứ tự theo số theo dõi (không đổi giữa các khung), người đang chọn luôn có trong danh sách
  const bad = people.filter((p) => p.violation).sort((a, b) => a.n - b.n), ok = people.filter((p) => !p.violation && !p.far),
    far = people.filter((p) => p.far);
  let listed = bad.slice(0, LIST_MAX);
  const picked = bad.find((p) => p.n === focus);
  if (picked && !listed.includes(picked)) listed = [...listed.slice(0, LIST_MAX - 1), picked];
  const range = ok.length && [Math.min(...ok.map((p) => p.score)), Math.max(...ok.map((p) => p.score))].map(pct);
  const Icon = BUTTON_ICONS[shutter.icon], Icon2 = secondary && BUTTON_ICONS[secondary.icon];
  return (
    <aside className="panel" aria-label="Kết quả kiểm tra">
      <header><b>HelmetCheck</b><button type="button" className="plain" aria-label="Thông tin" onClick={openInfo}><IconInfo /></button></header>
      <div className="segmented" role="group" aria-label="Chế độ">
        {MODES.map(([id, label]) => <button key={id} type="button" aria-pressed={mode === id} onClick={() => setMode(id)}>{label}</button>)}
      </div>
      <div className="verdict">
        <h2 aria-live="polite">{verdict && <span className={`dot ${verdict.tone}`} />}{verdict?.long ?? title}</h2>
        {metrics ? <dl className="tiles">{metrics.map(({ icon, value, label }) => <div key={icon}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
          : hint && <p>{hint}</p>}
      </div>
      <button type="button" className={`btn ${shutter.kind === "stop" ? "danger" : "primary"}`} onClick={shutter.onPress} disabled={shutter.disabled}>
        {Icon && <Icon />}{shutter.label}</button>
      {secondary && <button type="button" className="btn gray" onClick={secondary.onPress}>{Icon2 && <Icon2 />}{secondary.label}</button>}
      {DESKTOP && hasMedia && shutter.kind !== "stop" && <p className="note">hoặc kéo thả, dán ({PASTE_KEY}) ảnh / video khác vào trang</p>}
      {people.length > 0 && <>
        <h3>Người phát hiện</h3>
        <ul className="dark group people">
          {listed.map((p) => (
            <li key={p.n}><button type="button" className="rowbtn" aria-pressed={focus === p.n} onClick={() => setFocus(focus === p.n ? null : p.n)}>
              {cropSrc?.url ? <CropView {...cropSrc} box={p.box} className="crop" />
                : cropSrc?.canvas ? <FrameCrop canvas={cropSrc.canvas} box={p.box} t={cropSrc.t} />
                  : <span className="mini bad"><IconAlert size={18} stroke={3} /></span>}
              <span className="txt"><b className="badtext">Không đội mũ</b><span>{pct(p.score)}</span></span>
            </button></li>
          ))}
          {bad.length > LIST_MAX && <li><span className="rowbtn">
            <span className="mini bad"><IconAlert size={18} stroke={3} /></span>
            <span className="txt"><b className="badtext">và {bad.length - LIST_MAX} người không đội mũ khác</b><span>xem khung trên ảnh</span></span>
          </span></li>}
          {ok.length > 0 && <li><span className="rowbtn">
            <span className="mini ok"><IconCheck size={17} stroke={3} /></span>
            <span className="txt"><b>{ok.length} người đội mũ</b><span>{range[0] === range[1] ? range[0] : `${range[0]}–${range[1]}`}</span></span>
          </span></li>}
          {far.length > 0 && <li><span className="rowbtn">
            <span className="mini far" />
            <span className="txt"><b>{far.length} người ở xa</b><span>chưa đánh giá, không lưu ảnh</span></span>
          </span></li>}
        </ul>
      </>}
      <div className="recenthead"><h3>Lịch sử gần đây</h3>{recent.rows.length > 0 && <button type="button" className="link" onClick={() => onHistory()}>Xem tất cả</button>}</div>
      {recent.rows.length ? <ul className="recent">
        {recent.rows.map((r) => <li key={r.id}><button type="button" onClick={() => onHistory(r)} aria-label={`Mở ảnh vi phạm lúc ${timeFmt.format(r.at)}`}>
          <Crop rec={r} /><span>{timeFmt.format(r.at)}</span></button></li>)}
      </ul> : <p className="note left">Chưa có vi phạm nào được lưu trên máy này.</p>}
    </aside>
  );
}
const timeFmt = new Intl.DateTimeFormat("vi-VN", { hour: "2-digit", minute: "2-digit" });

// Xóa mô hình, thư viện đã lưu và cài đặt rồi tải lại từ mạng, thay cho việc vào Cài đặt Safari xóa dữ liệu trang. Lịch sử giữ nguyên
// (có nút Xóa tất cả riêng).
async function resetApp() {
  if (!window.confirm("Xóa mô hình đã tải và tải lại ứng dụng? Lịch sử vi phạm vẫn được giữ.")) return;
  for (const key of await caches.keys()) await caches.delete(key);
  try { localStorage.clear(); } catch { /* bộ nhớ trình duyệt bị chặn: không có gì để xóa */ }
  await (await navigator.serviceWorker?.getRegistration())?.unregister();
  location.reload();
}

function InfoSheet({ stats, rule, onClose }) {
  useEffect(() => {
    const esc = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", esc);
    return () => document.removeEventListener("keydown", esc);
  }, [onClose]);
  return (
    <div className="backdrop" onClick={onClose}>
      <section className="sheet" role="dialog" aria-modal="true" aria-labelledby="info-title" onClick={(e) => e.stopPropagation()}>
        <header><h2 id="info-title">Thông tin</h2><button type="button" className="done" onClick={onClose}>Xong</button></header>
        <ul className="group">{stats.map(([k, v]) => <li key={k}><span>{k}</span><b>{v}</b></li>)}</ul>
        <ul className="group"><li><button type="button" className="rowbtn destructive" onClick={resetApp}>Xóa dữ liệu đã tải, tải lại</button></li></ul>
        <p className="foot">{rule && `${ruleNote} `}Kết quả do mô hình gợi ý: người ở xa hoặc bị che có thể bị bỏ sót, một số người đội
          mũ có thể bị báo nhầm. Người ở xa (khung nét đứt) chưa được đánh giá và không được lưu ảnh. Ảnh chỉ lưu trên máy này.</p>
        <p className="foot">Đồ án tốt nghiệp của Đỗ Ngọc Phi, Trường Đại học Mỏ - Địa chất (2026), phi thương mại. Mô hình huấn luyện bằng Ultralytics YOLO (AGPL-3.0) trên SHEL5K (CC BY 4.0),
          SH17 (nhãn CC BY-NC-SA 4.0, ảnh Pexels) và Open Images V7 (nhãn CC BY 4.0); chạy bằng ONNX Runtime Web (MIT).{" "}
          <a href="https://github.com/phido0410/safety-helmet-detection" target="_blank" rel="noopener">Mã nguồn trên GitHub</a></p>
      </section>
    </div>
  );
}

function PhotoMode({ model, onSaved, chrome, dropped, consume }) {
  const [job, setJob] = useState(null);  // { url, width, height, people?, took?, saved? }
  const input = useRef(), gen = useRef(0);
  useEffect(() => () => job?.url && URL.revokeObjectURL(job.url), [job?.url]);
  useEffect(() => { if (dropped?.kind === "photo") { consume(); pick(dropped.file); } }, [dropped]);

  async function pick(file) {
    if (!file) return;
    chrome.notify(null);  // tệp mới: bỏ thông báo lỗi của tệp trước
    const g = ++gen.current, url = URL.createObjectURL(file);
    let bitmap;
    try { bitmap = await createImageBitmap(file); } catch {  // định dạng trình duyệt này không đọc được (vd. HEIC trên Chrome)
      URL.revokeObjectURL(url);
      return chrome.notify(BAD_FILE);
    }
    const base = { url, width: bitmap.width, height: bitmap.height };
    setJob(base);
    const m = await model.ready;
    const { dets, ms: took } = await m.run(bitmap, bitmap.width, bitmap.height);
    if (g !== gen.current) return;  // đã chọn ảnh khác trong lúc chờ
    const people = peopleOf(dets, m.cfg, bitmap.width, bitmap.height);
    let saved = people.some((p) => p.violation);
    if (saved) {
      try {
        await addCheck({ at: Date.now(), source: "Ảnh", width: bitmap.width, height: bitmap.height, people, ms: took,
          image: await snapshot(bitmap, bitmap.width, bitmap.height) });
        onSaved();
      } catch {  // duyệt riêng tư trên Safari không cho lưu ảnh vào IndexedDB: vẫn hiện kết quả
        chrome.notify(SAVE_FAILED);
        saved = false;
      }
    }
    setJob({ ...base, people, took, saved });
  }

  return (
    <>
      <input ref={input} type="file" accept="image/*" hidden onChange={(e) => { pick(e.target.files[0]); e.target.value = ""; }} />
      <Screen chrome={chrome} hint={job ? null : "Chọn một ảnh công trường để kiểm tra"} title={job ? "Đang phân tích…" : "Chưa có ảnh"}
        media={job && { width: job.width, height: job.height, node: <img src={job.url} alt="Ảnh đang kiểm tra" /> }}
        cropSrc={job && { url: job.url, width: job.width, height: job.height }}
        people={job?.people} verdict={job && (job.people ? verdictOf(job.people) : { tone: "none", text: "Đang phân tích…" })}
        metrics={job?.people && metricsOf(job.people, job.took, undefined, "ms xử lý ảnh")}
        shutter={{ kind: "pick", icon: "photo", label: job ? "Chọn ảnh khác" : "Chọn ảnh", onPress: () => input.current.click() }}
        secondary={job && { icon: "close", label: "Bỏ ảnh này", onPress: () => { gen.current++; setJob(null); } }}
        stats={[...baseStats(model), ["Xử lý ảnh", ms(job?.took)]]} />
    </>
  );
}

function VideoMode({ model, onSaved, chrome, dropped, consume }) {
  const [url, setUrl] = useState(null);
  const input = useRef();
  useEffect(() => () => url && URL.revokeObjectURL(url), [url]);
  useEffect(() => { if (dropped?.kind === "video") { consume(); setUrl(URL.createObjectURL(dropped.file)); } }, [dropped]);
  const pick = () => input.current.click();
  return (
    <>
      <input ref={input} type="file" accept="video/*" hidden onChange={(e) => {
        const f = e.target.files[0];
        if (f) { chrome.notify(null); setUrl(URL.createObjectURL(f)); }
        e.target.value = "";
      }} />
      {url ? <VideoRun key={url} url={url} model={model} onSaved={onSaved} chrome={chrome} onPick={pick} onClear={() => setUrl(null)} />
        : <Screen chrome={chrome} hint="Chọn một video công trường để kiểm tra" title="Chưa có video" stats={baseStats(model)} rule
          shutter={{ kind: "pick", icon: "video", label: "Chọn video", onPress: pick }} />}
    </>
  );
}

// Một video đã chọn: tracker riêng cho video này (key = url)
function VideoRun({ url, model, onSaved, chrome, onPick, onClear }) {
  const a = useAnalysis(model, onSaved, "Video");
  const [state, setState] = useState("ready");  // ready | playing | paused | done
  useEffect(() => () => a.stop(), []);

  function press() {
    const v = a.video.current;
    if (state === "done") return onPick();
    if (v.paused) { v.play(); setState("playing"); a.start(); } else { v.pause(); a.stop(); setState("paused"); }
  }
  const shutter = state === "playing" ? { kind: "stop", icon: "pause", label: "Tạm dừng" }
    : state === "done" ? { kind: "pick", icon: "video", label: "Chọn video khác" }
      : { kind: "rec", icon: "play", label: state === "paused" ? "Tiếp tục phân tích" : "Phát và phân tích" };
  const verdict = state === "ready" ? null
    : state === "done" ? (a.live.saved ? { tone: "bad", text: `Đã lưu ${a.live.saved} ảnh`, long: `Đã lưu ${a.live.saved} ảnh vi phạm` }
      : { tone: "ok", text: "Không có vi phạm", long: "Không có vi phạm" })
      : verdictOf(a.live.people, a.live.bad);
  return (
    <Screen chrome={chrome} live people={state === "done" ? [] : a.live.people} verdict={verdict} rule title="Video đã sẵn sàng"
      hint={state === "ready" ? "Bấm phát để phân tích" : null} metrics={state === "ready" || state === "done" ? null : metricsOf(a.live.people, a.live.took)}
      media={{ width: a.dims?.width ?? 16, height: a.dims?.height ?? 9,
        node: <video ref={a.video} src={url} playsInline muted onLoadedMetadata={a.fit} onEnded={() => { a.stop(); setState("done"); }}
          onError={() => { chrome.notify(BAD_FILE); onClear(); }} /> }}
      cropSrc={a.frame.current && { canvas: a.frame.current, t: a.live.t }}
      shutter={{ ...shutter, onPress: press }} secondary={{ icon: "close", label: "Bỏ video này", onPress: onClear }}
      stats={[...baseStats(model), ["Xử lý một khung", ms(a.live.took)], ["Tốc độ", fps(a.live.fps)], ["Đã lưu", `${a.live.saved} ảnh`]]} />
  );
}

function cameraError(err) {
  if (!navigator.mediaDevices) return "Trình duyệt không cho dùng camera ở trang này (cần mở bằng HTTPS).";
  if (err?.name === "NotAllowedError") return "Chưa được cấp quyền camera. Cho phép camera cho trang này trong cài đặt Safari rồi thử lại.";
  if (err?.name === "NotFoundError") return "Không tìm thấy camera trên máy này.";
  return `Không mở được camera: ${err?.message ?? err}`;
}

// Camera trực tiếp: nút đỏ mở camera, nút vuông tắt. Chỉ phân tích khi đang ở màn Kiểm tra và trang đang hiện (đỡ nóng máy, tốn pin).
function LiveMode({ model, onSaved, chrome, active }) {
  const [facing, setFacing] = useState("environment");
  const orient = useRef(null), facingNow = useRef(facing);
  facingNow.current = facing;
  const a = useAnalysis(model, onSaved, "Camera", () => orient.current?.get(facingNow.current) ?? 0, () => orient.current?.view());
  const [cam, setCam] = useState("off");  // off | opening | on | error
  const [error, setError] = useState(null);
  const stream = useRef(null), opening = useRef(0);
  const stopStream = () => { stream.current?.getTracks().forEach((t) => t.stop()); stream.current = null; };

  async function open(face) {
    const g = ++opening.current;
    setCam("opening");
    try {
      stopStream();
      const s = await navigator.mediaDevices.getUserMedia(camera(face));
      if (g !== opening.current) return s.getTracks().forEach((t) => t.stop());  // đã bấm tắt trong lúc chờ quyền camera
      stream.current = s;
      a.video.current.srcObject = s;
      await a.video.current.play();
      setCam("on");
    } catch (err) {
      if (g !== opening.current) return;
      stopStream(); setError(cameraError(err)); setCam("error");
    }
  }
  function close() {
    opening.current++;
    a.stop(); stopStream();
    if (a.video.current) a.video.current.srcObject = null;
    setCam("off");
  }
  useEffect(() => () => { opening.current++; a.stop(); stopStream(); orient.current?.stop(); }, []);
  useEffect(() => {
    const sync = () => (cam === "on" && active && !document.hidden ? a.start() : a.stop());
    sync();
    document.addEventListener("visibilitychange", sync);
    return () => document.removeEventListener("visibilitychange", sync);
  }, [cam, active]);

  const flip = () => {
    const f = facing === "environment" ? "user" : "environment";
    setFacing(f);
    a.reset();
    if (cam === "on") open(f);
  };
  const shutter = cam === "on" ? { kind: "stop", icon: "stop", label: "Tắt camera", onPress: close }
    // cảm biến hướng phải xin quyền ngay trong lần bấm này (iOS); có rồi thì dùng tiếp
    : { kind: "rec", icon: "camera", label: cam === "opening" ? "Đang mở camera" : "Mở camera", disabled: cam === "opening",
      onPress: () => { orient.current ??= watchOrientation(); open(facing); } };
  return (
    <Screen chrome={chrome} live rule shutter={shutter} title="Camera đang tắt"
      people={cam === "on" ? a.live.people : []}
      verdict={cam === "on" ? (a.live.t ? verdictOf(a.live.people, a.live.bad) : { tone: "none", text: "Đang phân tích…", long: "Đang phân tích…" }) : null}
      metrics={cam === "on" && a.live.t ? metricsOf(a.live.people, a.live.took, a.live.turn) : null}
      hint={cam === "error" ? error : cam === "off" ? (chrome.wide ? "Bấm Mở camera để bắt đầu" : "Bấm nút đỏ để mở camera") : null}
      media={{ width: a.dims?.width ?? 9, height: a.dims?.height ?? 16,
        node: <video ref={a.video} playsInline muted autoPlay onLoadedMetadata={a.fit} onResize={a.fit} /> }}
      secondary={{ icon: "flip", label: "Đổi camera trước / sau", onPress: flip }}
      cropSrc={cam === "on" && a.frame.current ? { canvas: a.frame.current, t: a.live.t } : null}
      stats={[...baseStats(model), ["Xử lý một khung", ms(a.live.took)], ["Tốc độ", fps(a.live.fps)], ["Xoay khung theo hướng cầm máy", `${a.live.rot ?? 0}°`],
        ["Lệch hướng so với ảnh vừa lưu", a.live.turn != null ? deg(a.live.turn) : a.live.sensor ? "chưa lưu ảnh" : "không có cảm biến"],
        ["Đã lưu", `${a.live.saved} ảnh`]]} />
  );
}

// Vòng phân tích dùng chung cho video và camera: chép khung hình hiện tại ra canvas, chạy mô hình (khung mới tới khi lần trước chưa
// xong thì bỏ qua), theo dõi từng người qua các khung, tự lưu ảnh khi có người không đội mũ chưa được chụp. Ảnh lưu chính là canvas
// vừa phân tích (đã xoay thẳng) nên khung khoanh khớp ảnh. Mỗi lần start() là một thế hệ mới: vòng cũ còn đang chờ mô hình sẽ tự dừng, không chạy
// song song hai vòng. Tracker sống cùng màn video/camera nên tạm dừng rồi chạy tiếp vẫn nhớ ai đã bị chụp.
// getRotation (camera): góc xoay khung theo hướng cầm máy (lib/orientation.js); mô hình chạy trên khung đã xoay thẳng, khung khoanh
// được xoay ngược về khung gốc để vẽ và theo dõi; ảnh lưu là khung đã xoay thẳng, khung khoanh xoay theo. getView (camera): hướng camera cho tracker (lia máy
// sang cảnh khác thì quên người đã chụp).
function useAnalysis(model, onSaved, source, getRotation, getView) {
  const video = useRef(), frame = useRef(null), upright = useRef(null);
  const [tracker] = useState(createTracker);
  const [dims, setDims] = useState(null);
  const [live, setLive] = useState({ people: [], took: 0, fps: 0, saved: 0, t: 0 });
  const st = useRef({ gen: 0, running: false, busy: false, lastCapture: -Infinity, saved: 0, last: 0, ran: 0, since: 0 });

  function fit() {
    const v = video.current, k = Math.min(1, FRAME_MAX_SIDE / Math.max(v.videoWidth, v.videoHeight));
    frame.current ??= document.createElement("canvas");
    frame.current.width = Math.round(v.videoWidth * k);
    frame.current.height = Math.round(v.videoHeight * k);
    setDims({ width: frame.current.width, height: frame.current.height });
  }

  async function step(gen) {
    const v = video.current, s = st.current;
    if (!s.running || gen !== s.gen || !v) return;
    if (!s.busy && v.readyState >= 2 && frame.current) {
      s.busy = true;
      const c = frame.current, t = source === "Camera" ? (s.ran + performance.now() - s.since) / 1000 : v.currentTime;
      c.getContext("2d").drawImage(v, 0, 0, c.width, c.height);
      const rot = getRotation?.() ?? 0;
      let src = c;
      if (rot) {
        const r = (upright.current ??= document.createElement("canvas")), [w, h] = rot % 180 ? [c.height, c.width] : [c.width, c.height];
        if (r.width !== w || r.height !== h) Object.assign(r, { width: w, height: h });
        const g = r.getContext("2d");
        g.setTransform(...rotationMatrix(rot, c.width, c.height));
        g.drawImage(c, 0, 0);
        g.setTransform(1, 0, 0, 1, 0, 0);
        src = r;
      }
      const m = await model.ready;
      const { dets, ms: took } = await m.run(src, src.width, src.height);
      s.busy = false;
      if (!s.running || gen !== s.gen) return;
      // quy tắc của app tính trên khung thẳng đứng (chiều cao người đúng chiều), rồi khung khoanh mới xoay ngược về khung gốc
      const found = peopleOf(dets, m.cfg, src.width, src.height).map((p) => (rot ? { ...p, box: unrotateBox(p.box, rot, c.width, c.height) } : p));
      // đồng hồ của tracker: thời gian của video hoặc thời gian camera đã phân tích, đều không tính lúc tạm dừng
      const view = getView?.(), { people, proof, due, bad } = tracker.update(found, t * 1000, view), now = performance.now();
      if (due.length && now - s.lastCapture >= CAPTURE_EVERY_MS) {
        tracker.captured();
        s.lastCapture = now;
        s.captureView = view;
        s.saved++;
        // cầm ngang khi khóa xoay dọc: lưu khung đã xoay thẳng, không phải khung camera nằm nghiêng
        const kept = rot ? proof.map((p) => ({ ...p, box: rotateBox(p.box, rot, c.width, c.height) })) : proof;
        snapshot(src, src.width, src.height).then((image) => addCheck({ at: Date.now(), source,
          ...(source === "Video" && { videoTime: t }), width: src.width, height: src.height, people: kept, ms: took, image })).then(onSaved);
      }
      if (s.saved) s.captureView ??= view;  // lưu lúc cảm biến chưa có số đo: lấy số đo đầu tiên làm mốc, như tracker
      // lệch hướng camera so với lúc lưu ảnh gần nhất: quá VIEW_DEG thì tracker coi là cảnh mới (hiện để kiểm tra trên máy thật)
      const turn = getView ? (view && s.captureView ? viewAngle(s.captureView, view) : null) : undefined;
      setLive({ people, bad, took, fps: s.last ? 1000 / (now - s.last) : 0, saved: s.saved, t, rot, turn, sensor: !!view });
      s.last = now;
    }
    if (v.requestVideoFrameCallback) v.requestVideoFrameCallback(() => step(gen));
    else requestAnimationFrame(() => step(gen));
  }

  const start = () => {
    const s = st.current;
    if (s.running) return;
    Object.assign(s, { running: true, gen: s.gen + 1, last: 0, since: performance.now() });
    step(s.gen);
  };
  // camera: đồng hồ chỉ chạy khi đang phân tích (như thời gian video), để tạm dừng hay xem Lịch sử rồi quay lại không làm tracker
  // coi mọi người là mới và chụp lại
  const stop = () => {
    const s = st.current;
    if (s.running) Object.assign(s, { running: false, ran: s.ran + performance.now() - s.since });
  };
  return { video, frame, dims, live, fit, start, stop, reset: tracker.reset };
}
