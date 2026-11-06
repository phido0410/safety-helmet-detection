import { useEffect, useState } from "react";

const WIDE = "(min-width: 900px) and (orientation: landscape)";  // máy tính, iPad xoay ngang: ảnh bên trái, bảng bên phải

export function useWide() {
  const [wide, setWide] = useState(() => matchMedia(WIDE).matches);
  useEffect(() => {
    const m = matchMedia(WIDE), on = () => setWide(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);
  return wide;
}
