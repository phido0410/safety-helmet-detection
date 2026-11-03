import { createRoot } from "react-dom/client";
import "./styles.css";
import App from "./App.jsx";

createRoot(document.getElementById("root")).render(<App />);

// Chạy offline sau lần mở đầu (mô hình + onnxruntime-web được lưu lại); chỉ bản build, bản dev luôn lấy file mới
if (import.meta.env.PROD && "serviceWorker" in navigator) navigator.serviceWorker.register("sw.js");
