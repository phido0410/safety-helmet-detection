// Biểu tượng vẽ tay theo dáng SF Symbols: nét 2 px, đầu và góc tròn
const Svg = ({ children, size = 24, stroke = 2 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke}
    strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{children}</svg>
);

export const IconInfo = (p) => <Svg {...p}><circle cx="12" cy="12" r="9" /><path d="M12 11v5.5M12 7.6v.1" /></Svg>;
export const IconFlip = (p) => <Svg {...p}><path d="M4 8h3l2-3h6l2 3h3v11H4z" /><path d="M9.5 12.5a2.7 2.7 0 0 1 4.6-1.4l.9.9M14.5 14a2.7 2.7 0 0 1-4.6 1.4l-.9-.9M15 10v2h-2M9 16v-2h2" /></Svg>;
export const IconClose = (p) => <Svg {...p}><path d="M7 7l10 10M17 7 7 17" /></Svg>;
export const IconChevron = (p) => <Svg {...p}><path d="m9.5 6 6 6-6 6" /></Svg>;
export const IconBack = (p) => <Svg {...p}><path d="M15 5.5 8.5 12l6.5 6.5" /></Svg>;
export const IconTrash = (p) => <Svg {...p}><path d="M4.5 7h15M9.5 7V4.8h5V7M6.5 7l.9 12.2h9.2L17.5 7M10 10.5v5.5M14 10.5v5.5" /></Svg>;
export const IconAlert = (p) => <Svg {...p}><path d="M12 6.5v7M12 17.4v.1" /></Svg>;
export const IconCheck = (p) => <Svg {...p}><path d="m6.5 12.5 3.5 3.5 7.5-8" /></Svg>;
export const IconStack = (p) => <Svg {...p}><rect x="4" y="7" width="16" height="13" rx="3" /><path d="M7 4h10" /></Svg>;
export const IconPhoto = (p) => <Svg {...p}><rect x="3.5" y="5" width="17" height="14" rx="2.5" /><path d="m4 17 5-5 4 4 2.5-2.5 4.5 4.5" /><circle cx="15.5" cy="9.5" r="1.5" /></Svg>;
export const IconVideo = (p) => <Svg {...p}><rect x="3" y="6" width="13" height="12" rx="2.5" /><path d="m16 10.5 5-3v9l-5-3" /></Svg>;
export const IconPlay = (p) => <Svg {...p}><path d="M8 5.5v13l10.5-6.5z" /></Svg>;
export const IconPause = (p) => <Svg {...p}><path d="M8.5 5.5v13M15.5 5.5v13" /></Svg>;
export const IconCamera = (p) => <Svg {...p}><path d="M4 8h3l2-3h6l2 3h3v11H4z" /><circle cx="12" cy="13" r="3.5" /></Svg>;
export const IconStop = (p) => <Svg {...p}><rect x="6.5" y="6.5" width="11" height="11" rx="2" /></Svg>;
export const IconPerson = (p) => <Svg {...p}><circle cx="12" cy="8" r="3.6" /><path d="M5 20a7 7 0 0 1 14 0" /></Svg>;
export const IconCompass = (p) => <Svg {...p}><circle cx="12" cy="12" r="8.5" /><path d="m15 9-1.9 4.1L9 15l1.9-4.1z" /></Svg>;
export const IconTimer = (p) => <Svg {...p}><circle cx="12" cy="13" r="7.5" /><path d="M12 13V9.5M9.5 3h5" /></Svg>;
export const IconUpload = (p) => <Svg {...p}><path d="M12 15V4.5M7.5 9 12 4.5 16.5 9M4.5 15v4.5h15V15" /></Svg>;
