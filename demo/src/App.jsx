import { useEffect, useState } from "react";
import CheckView from "./components/CheckView.jsx";
import HistoryView from "./components/HistoryView.jsx";
import { listChecks } from "./lib/history.js";
import { loadModel } from "./lib/model.js";

export default function App() {
  const [view, setView] = useState({ name: "check" });  // history: { name, rec } mở sẵn một ảnh
  const [model, setModel] = useState({ status: "loading", progress: 0 });
  const [version, setVersion] = useState(0);  // tăng khi lịch sử đổi
  const [recent, setRecent] = useState({ rec: null, rows: [], unseen: 0 });

  useEffect(() => {
    const ready = loadModel((progress) => setModel((m) => ({ ...m, progress })), (backend) => setModel((m) => ({ ...m, backend })));
    setModel((m) => ({ ...m, ready }));
    ready.then((m) => setModel((s) => ({ ...s, status: "ready", backend: m.backend, name: m.cfg.name })),
      (err) => setModel((s) => ({ ...s, status: "error", error: err.message })));
  }, []);
  useEffect(() => {
    listChecks().then((rows) => setRecent({ rec: rows[0] ?? null, rows: rows.slice(0, 4), unseen: rows.filter((r) => !r.seen).length }));
  }, [version]);

  const changed = () => setVersion((v) => v + 1);
  return (
    <div className="app">
      {/* màn Kiểm tra luôn giữ trong cây để camera / video không mất khi xem lịch sử rồi quay lại */}
      <main hidden={view.name !== "check"}>
        <CheckView model={model} active={view.name === "check"} recent={recent} onSaved={changed}
          onHistory={(rec) => setView({ name: "history", rec })} />
      </main>
      {view.name === "history" && <main>
        <HistoryView version={version} initial={view.rec} onChange={changed} onClose={() => setView({ name: "check" })} />
      </main>}
    </div>
  );
}
