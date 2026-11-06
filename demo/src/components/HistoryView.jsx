import { useEffect, useRef, useState } from "react";
import Stage, { Capsule, peopleCount, verdictOf } from "./Stage.jsx";
import Crop, { Zooms, useObjectUrl } from "./Crop.jsx";
import { IconBack, IconChevron, IconStack, IconTrash } from "./Icons.jsx";
import { clearChecks, deleteCheck, listChecks, markSeen } from "../lib/history.js";
import { violators } from "../lib/crop.js";
import { useWide } from "../lib/wide.js";

const timeFmt = new Intl.DateTimeFormat("vi-VN", { hour: "2-digit", minute: "2-digit" });
const dateFmt = new Intl.DateTimeFormat("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
const dayKey = (t) => new Date(t).toDateString();
function dayLabel(t) {
  const today = new Date(), yesterday = new Date(today - 864e5);
  return dayKey(t) === today.toDateString() ? "Hôm nay" : dayKey(t) === yesterday.toDateString() ? "Hôm qua" : dateFmt.format(t);
}
const badCount = (rec) => rec.people.filter((p) => p.violation).length;

// Lịch sử vi phạm kiểu danh sách iOS: nhóm theo ngày, mỗi dòng là ảnh cắt người vi phạm + số người không mũ + giờ, nguồn; chấm xanh
// là dòng chưa xem. Chạm một dòng để mở ảnh đầy đủ có khung.
export default function HistoryView({ version, initial, onChange, onClose }) {
  const [rows, setRows] = useState(null);
  const [open, setOpen] = useState(initial ?? null);  // mở thẳng một ảnh (từ lịch sử gần đây ở bảng bên phải)
  useEffect(() => { listChecks().then(setRows); }, [version]);
  const fromPanel = useRef(!!initial);  // mở từ bảng bên phải: nút quay lại về thẳng màn Kiểm tra
  useEffect(() => {
    if (initial) markSeen(initial.id).then((rec) => { if (rec) setOpen((o) => (o?.id === rec.id ? rec : o)); onChange(); });
  }, []);

  const openRow = async (r) => { setOpen((await markSeen(r.id)) ?? r); onChange(); };
  const toCheck = fromPanel.current && open?.id === initial?.id;  // mở từ bảng bên phải: quay lại thẳng màn Kiểm tra
  if (open) return <Detail rec={open} backLabel={toCheck ? "Màn hình chính" : "Lịch sử"} onBack={() => (toCheck ? onClose() : setOpen(null))}
    onDelete={async () => { await deleteCheck(open.id); setOpen(null); onChange(); }} />;

  const days = [];
  for (const r of rows ?? []) {
    const last = days.at(-1);
    if (last?.key === dayKey(r.at)) last.rows.push(r);
    else days.push({ key: dayKey(r.at), label: dayLabel(r.at), rows: [r] });
  }
  return (
    <section className="ios" aria-labelledby="history-title">
      <nav className="navbar"><button type="button" className="link" onClick={onClose}><IconBack size={22} />Màn hình chính</button><span /></nav>
      <h1 id="history-title" className="large">Lịch sử</h1>
      <p className="sub">Lưu trên máy này</p>
      {rows?.length === 0 && (
        <div className="empty">
          <span className="emptyicon"><IconStack size={34} /></span>
          <h2>Chưa có vi phạm</h2>
          <p>Khi phát hiện người không đội mũ, ảnh được lưu ở đây, chỉ trên máy này.</p>
        </div>
      )}
      {days.map((d) => (
        <section key={d.key} aria-label={d.label}>
          <h3 className="grouptitle">{d.label}</h3>
          <ul className="group list">
            {d.rows.map((r) => (
              <li key={r.id}>
                <button type="button" className="rowbtn" onClick={() => openRow(r)}>
                  <Crop rec={r} className="crop" />
                  <span className="txt"><b>{badCount(r)} vi phạm không đội mũ</b><span>{timeFmt.format(r.at)} · {r.source}</span></span>
                  {!r.seen && <span className="unread" aria-label="Mới" />}
                  <IconChevron size={18} />
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}
      {rows?.length > 0 && (
        <ul className="group">
          <li><button type="button" className="rowbtn destructive" onClick={async () => {
            if (window.confirm(`Xóa toàn bộ ${rows.length} ảnh trong lịch sử? Không khôi phục được.`)) { await clearChecks(); onChange(); }
          }}>Xóa tất cả</button></li>
        </ul>
      )}
    </section>
  );
}

function Detail({ rec, backLabel, onBack, onDelete }) {
  const url = useObjectUrl(rec.image), wide = useWide();
  const [zoom, setZoom] = useState(false);
  // chuyển màn thì nút vừa bấm biến mất: đưa tiêu điểm sang màn mới và trả lại nút khi quay về, để bàn phím, VoiceOver không mất chỗ
  const heading = useRef(), button = useRef(), pushed = useRef(false);
  useEffect(() => {
    if (zoom) { heading.current?.focus(); pushed.current = true; } else if (pushed.current) button.current?.focus();
  }, [zoom]);
  const verdict = verdictOf(rec.people), bad = violators(rec.people).length, when = `${timeFmt.format(rec.at)}, ${dateFmt.format(rec.at)}`;
  const meta = `${peopleCount(rec.people)} · ${rec.source} · ${when} · ${Math.round(rec.ms)}\u00a0ms`;
  if (zoom && !wide) return (
    <section className="detail" aria-label="Chi tiết vi phạm">
      <nav className="navbar dark"><button type="button" className="link" onClick={() => setZoom(false)}><IconBack size={22} />Ảnh vi phạm</button><span /></nav>
      <div className="zoomscreen">
        <h1 ref={heading} tabIndex={-1}>{verdict.long}</h1>
        <p>{rec.source} · {when}</p>
        <Zooms url={url} rec={rec} />
      </div>
    </section>
  );
  return (
    <section className={`detail${wide ? " wide" : ""}`} aria-label="Ảnh vi phạm">
      <div className="shot">
        <nav className="navbar dark">
          <button type="button" className="link" onClick={onBack}><IconBack size={22} />{backLabel}</button>
          <button type="button" className="link danger" aria-label="Xóa ảnh này"
            onClick={() => window.confirm("Xóa ảnh này khỏi lịch sử?") && onDelete()}><IconTrash /></button>
        </nav>
        <div className="viewfinder">
          <Stage width={rec.width} height={rec.height} people={rec.people}><img src={url} alt="Ảnh vi phạm đã lưu" /></Stage>
        </div>
      </div>
      {wide ? (
        <aside className="panel" tabIndex={0} aria-label="Chi tiết vi phạm">
          <div className="verdict"><h2><span className={`dot ${verdict.tone}`} />{verdict.long}</h2><p>{meta}</p></div>
          {bad > 0 && <Zooms url={url} rec={rec} />}
        </aside>
      ) : (
        <footer className="meta">
          <Capsule {...verdict} />
          <p>{meta}</p>
          {bad > 0 && <button type="button" ref={button} className="btn primary" onClick={() => setZoom(true)}>Xem chi tiết {bad} người<IconChevron size={20} stroke={2.5} /></button>}
        </footer>
      )}
    </section>
  );
}
