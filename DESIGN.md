---
name: HelmetCheck
description: On-device hard-hat check for Vietnamese construction sites, built as the iPhone Camera app pointed at people.
colors:
  violation-orange: "#e2541b"
  helmet-green: "#14945f"
  violation-ink: "#b83d0c"
  helmet-ink: "#0e7349"
  record-red: "#ff3b30"
  mode-yellow: "#ffd60a"
  tint: "#007aff"
  tint-dark: "#0a84ff"
  camera-black: "#000000"
  control-white: "#ffffff"
  glass: "rgba(0, 0, 0, 0.6)"
  round-fill: "rgba(255, 255, 255, 0.14)"
  label: "#000000"
  label-secondary: "#6c6c70"
  separator: "rgba(60, 60, 67, 0.29)"
  grouped-bg: "#f2f2f7"
  cell: "#ffffff"
  fill: "#e5e5ea"
  label-dark: "#ffffff"
  label-secondary-dark: "rgba(235, 235, 245, 0.6)"
  separator-dark: "rgba(84, 84, 88, 0.65)"
  grouped-bg-dark: "#000000"
  cell-dark: "#1c1c1e"
  fill-dark: "#2c2c2e"
  panel-bg: "#1c1c1e"
  panel-cell: "#2c2c2e"
  gray-fill: "#3a3a3c"
  segment-track: "rgba(118, 118, 128, 0.24)"
  segment-selected: "#636366"
  violation-text-dark: "#ff8a5c"
  focus-wash: "rgba(10, 132, 255, 0.22)"
typography:
  large-title:
    fontFamily: "-apple-system, BlinkMacSystemFont, SF Pro Text, Helvetica Neue, system-ui, sans-serif"
    fontSize: "34px"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "-0.02em"
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, SF Pro Text, Helvetica Neue, system-ui, sans-serif"
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1.3
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, SF Pro Text, Helvetica Neue, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.3
  body-strong:
    fontFamily: "-apple-system, BlinkMacSystemFont, SF Pro Text, Helvetica Neue, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 600
    lineHeight: 1.3
  subhead:
    fontFamily: "-apple-system, BlinkMacSystemFont, SF Pro Text, Helvetica Neue, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.3
  mode-label:
    fontFamily: "-apple-system, BlinkMacSystemFont, SF Pro Text, Helvetica Neue, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    letterSpacing: "0.08em"
  section-header:
    fontFamily: "-apple-system, BlinkMacSystemFont, SF Pro Text, Helvetica Neue, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    letterSpacing: "0.02em"
  footnote:
    fontFamily: "-apple-system, BlinkMacSystemFont, SF Pro Text, Helvetica Neue, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.4
  verdict-title:
    fontFamily: "-apple-system, BlinkMacSystemFont, SF Pro Text, Helvetica Neue, system-ui, sans-serif"
    fontSize: "26px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  segment-label:
    fontFamily: "-apple-system, BlinkMacSystemFont, SF Pro Text, Helvetica Neue, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 500
  caption:
    fontFamily: "-apple-system, BlinkMacSystemFont, SF Pro Text, Helvetica Neue, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 400
rounded:
  box: "6px"
  stop: "7px"
  thumb: "10px"
  crop: "12px"
  tag: "13px"
  panel-group: "14px"
  segment: "15px"
  segment-track: "18px"
  drop: "24px"
  pill: "25px"
  capsule: "20px"
  group: "20px"
  sheet: "28px"
  full: "50%"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  mode-gap: "20px"
  xl: "24px"
  xxl: "32px"
components:
  glass-button:
    backgroundColor: "{colors.glass}"
    textColor: "{colors.control-white}"
    rounded: "{rounded.full}"
    size: "44px"
  verdict-capsule:
    backgroundColor: "{colors.glass}"
    textColor: "{colors.control-white}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.capsule}"
    height: "40px"
    padding: "0 16px 0 13px"
  round-button:
    backgroundColor: "{colors.round-fill}"
    textColor: "{colors.control-white}"
    rounded: "{rounded.full}"
    size: "52px"
  shutter:
    backgroundColor: "{colors.control-white}"
    rounded: "{rounded.full}"
    size: "78px"
  shutter-stop:
    backgroundColor: "{colors.record-red}"
    rounded: "{rounded.stop}"
    size: "30px"
  mode-button:
    textColor: "{colors.control-white}"
    typography: "{typography.mode-label}"
    height: "44px"
    padding: "0 4px"
  mode-button-active:
    textColor: "{colors.mode-yellow}"
    typography: "{typography.mode-label}"
  history-thumb:
    backgroundColor: "{colors.cell-dark}"
    rounded: "{rounded.thumb}"
    size: "52px"
  count-badge:
    backgroundColor: "{colors.violation-ink}"
    textColor: "{colors.control-white}"
    rounded: "11px"
    height: "22px"
    padding: "0 6px"
  violator-badge:
    backgroundColor: "{colors.violation-orange}"
    textColor: "{colors.control-white}"
    rounded: "{rounded.full}"
    size: "24px"
  helmet-badge:
    backgroundColor: "{colors.helmet-green}"
    textColor: "{colors.control-white}"
    rounded: "{rounded.full}"
    size: "24px"
  confidence-tag:
    backgroundColor: "{colors.violation-ink}"
    textColor: "{colors.control-white}"
    rounded: "{rounded.tag}"
    padding: "4px 10px"
  grouped-list:
    backgroundColor: "{colors.cell}"
    textColor: "{colors.label}"
    rounded: "{rounded.group}"
    padding: "0 16px"
  history-row:
    backgroundColor: "{colors.cell}"
    textColor: "{colors.label}"
    height: "76px"
    padding: "10px 14px 10px 12px"
  sheet:
    backgroundColor: "{colors.grouped-bg}"
    textColor: "{colors.label}"
    rounded: "{rounded.sheet}"
    padding: "12px 16px 24px"
  text-button:
    textColor: "{colors.tint}"
    typography: "{typography.body-strong}"
    height: "44px"
  panel:
    backgroundColor: "{colors.panel-bg}"
    textColor: "{colors.control-white}"
    padding: "16px 24px 24px"
    width: "clamp(340px, 28vw, 400px)"
  segmented-control:
    backgroundColor: "{colors.segment-track}"
    rounded: "{rounded.segment-track}"
    padding: "3px"
  segmented-button:
    textColor: "{colors.control-white}"
    typography: "{typography.segment-label}"
    rounded: "{rounded.segment}"
    height: "38px"
  segmented-button-active:
    backgroundColor: "{colors.segment-selected}"
    textColor: "{colors.control-white}"
    rounded: "{rounded.segment}"
  panel-verdict:
    textColor: "{colors.control-white}"
    typography: "{typography.verdict-title}"
  button-primary:
    backgroundColor: "{colors.tint-dark}"
    textColor: "{colors.control-white}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.pill}"
    height: "50px"
  button-danger:
    backgroundColor: "{colors.record-red}"
    textColor: "{colors.control-white}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.pill}"
    height: "50px"
  button-gray:
    backgroundColor: "{colors.gray-fill}"
    textColor: "{colors.control-white}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.pill}"
    height: "50px"
  people-list:
    backgroundColor: "{colors.panel-cell}"
    textColor: "{colors.control-white}"
    rounded: "{rounded.panel-group}"
  people-row:
    textColor: "{colors.control-white}"
    height: "60px"
    padding: "8px 12px"
  people-row-selected:
    backgroundColor: "{colors.focus-wash}"
  people-crop:
    backgroundColor: "{colors.gray-fill}"
    rounded: "{rounded.thumb}"
    size: "40px"
  mini-badge-violator:
    backgroundColor: "{colors.violation-ink}"
    textColor: "{colors.control-white}"
    rounded: "{rounded.thumb}"
    size: "40px"
  mini-badge-helmet:
    backgroundColor: "{colors.helmet-ink}"
    textColor: "{colors.control-white}"
    rounded: "{rounded.thumb}"
    size: "40px"
  recent-crop:
    backgroundColor: "{colors.gray-fill}"
    rounded: "{rounded.crop}"
  drop-zone:
    textColor: "{colors.control-white}"
    rounded: "{rounded.drop}"
    padding: "24px"
---

# Design System: HelmetCheck

## Overview

**Creative North Star: "The Camera, Pointed at People"**

HelmetCheck is the iPhone Camera app with one extra job: it answers "who has no hard hat" on top of the viewfinder. Everything that is not the image is iOS system material: the system font, black camera chrome, white controls, the Camera-app mode row with its yellow active label, the round shutter, and the last-capture thumbnail. The history is a stock iOS grouped list that follows light and dark appearance. Nothing is branded beyond the two signal colours, so the image and the boxes carry the screen.

Density is minimal by design: one floating verdict capsule, coloured boxes with round glyph badges, and a single line of hint text in the empty viewfinder. Three numbers sit on the camera screen in a small glass metrics bar just above the mode row, where the Camera app keeps its zoom pills, so it covers feet and ground rather than heads: people in frame, heading change since the last saved image (live camera only) and processing time per frame (chosen by the student 2026-11-04). Everything else (model, threads, frame rate, frame rotation, saved count) lives in the info sheet one tap away. On a phone or a portrait iPad the camera screen fills the full width; on a landscape viewport of 900px or more the same black viewfinder sits beside a dark iOS side panel that spells out what the capsule abbreviates, the way an iPad app shows a detail column.

The world replaced an earlier drafting-sheet direction ("Bản vẽ thi công") after it proved hard to read on the phone; title blocks, condensed display type, grid paper and stat stacks are not part of this system.

**Key Characteristics:**
- System font stack only; iOS type sizes (34 / 20 / 17 / 15 / 13; the wide panel adds 26 for its verdict and 12 for captions).
- Black, full-bleed camera chrome; media letterboxed, never cropped.
- Two signal colours with fixed meaning: orange = no hard hat, green = hard hat, always paired with a glyph ("!" / ✓) or words.
- Glass (blurred black) for anything floating over the image.
- iOS grouped lists with paired light/dark tokens for every non-camera screen.
- Capability decides the device, not the user agent: no touch screen = desktop (ẢNH and VIDEO only, drop and paste); ≥ 900px landscape = viewfinder plus dark panel.

## Colors

A black-and-white camera shell with two semantic signal colours and the iOS system accents; no decorative colour.

### Primary
- **Violation Orange** (violation-orange): every "no hard hat" mark: the violator box stroke and 28% fill, the "!" badge, the verdict dot and the inset ring on history crops. Small white text never sits on it: the violator's confidence tag and the unseen-count badge use **Violation Ink** (violation-ink, #b83d0c, 5.7:1 with white). Darker than the report's figure orange so it reads in sunlight. On the dark wide panel, the words naming a violator ("Không đội mũ", "và N người không đội mũ khác") use **Violation Text (dark)** (violation-text-dark), a lighter orange that reads on the panel cell; the 40px mini badges beside them sit on violation-ink.

### Secondary
- **Helmet Green** (helmet-green): "wearing a hard hat" only: the 2px helmet box outline, the ✓ badge and the "Tất cả đội mũ" verdict dot. The helmet confidence tag uses **Helmet Ink** (helmet-ink, #0e7349, 5.9:1 with white).

### Tertiary
- **Record Red** (record-red): the running state of the shutter (filled disc before start, rounded square while running), the panel's stop button while a camera or video runs ("Tắt camera", "Tạm dừng"), and destructive actions ("Xóa tất cả", trash). Never used for detections.
- **Mode Yellow** (mode-yellow): the active label in the mode row, nothing else.
- **System Tint** (tint, tint-dark in dark appearance, on the black detail screen and throughout the wide panel): text buttons ("Xong", back link, "Xem tất cả"), the unread dot, the focus ring, the panel's primary button fill, the drag-over outline, and the selected people row wash (**Focus Wash**, focus-wash: tint-dark at 22%).

### Neutral
- **Camera Black** (camera-black): background of the camera screen, controls bar, detail screen, letterbox bars and PWA theme colour.
- **Control White** (control-white): shutter ring and disc, glyph colour on glass, text on signal fills.
- **Glass** (glass): behind the info button and the verdict capsule, always with backdrop blur.
- **Round Fill** (round-fill): the 52px side button (switch camera / clear file).
- **iOS grouped tokens** (label, label-secondary, separator, grouped-bg, cell, fill and their `-dark` pairs): history, info sheet and empty states, switched by `prefers-color-scheme`.
- **Panel material** (panel-bg, panel-cell, gray-fill): the wide layout's right column is iOS dark material in both appearances, like the camera screen it belongs to: panel-bg surface (same value as cell-dark), panel-cell for its grouped list, gray-fill for the secondary button, crop placeholders and the panel scrollbar. Secondary text in the panel uses label-secondary-dark, separators separator-dark.
- **Segment track / selected** (segment-track, segment-selected): the iOS segmented control in the panel.

### Named Rules
**The Two Signals Rule.** Orange means no hard hat and green means hard hat, everywhere and only there. No other element may use either hue.

**The Never Colour Alone Rule.** A signal colour always travels with a glyph ("!" / ✓) or a word ("2 không mũ", "Không đội mũ · 87%"). The violator box additionally differs in form (3px stroke plus fill vs 2px outline), so it stays distinct when a ✓ badge is dropped.

## Typography

**Display Font:** none; the system stack (-apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", system-ui, sans-serif)
**Body Font:** same stack
**Label/Mono Font:** same stack; figures use `tabular-nums` in list values

**Character:** San Francisco on the iPhone, used at the iOS text-style sizes, so the app reads as part of the OS rather than a website.

### Hierarchy
- **Large Title** (700, 34px, -0.02em): "Lịch sử" at the top of the history screen only.
- **Title** (700, 20px): sheet title "Thông tin"; the empty-state heading uses 22px/700.
- **Body** (400, 17px, 1.3): default text, list rows, hint line in the empty viewfinder (white at 75%).
- **Body Strong** (600, 17px): verdict capsule text, row titles ("3 không đội mũ"), "Xong".
- **Subhead** (400, 15px): row secondary line (time · source), history subtitle, detail meta line; the confidence tag uses 15px/600.
- **Mode Label** (600, 13px, 0.08em, uppercase): ẢNH · VIDEO · TRỰC TIẾP in the camera mode row.
- **Section Header** (400, 13px, 0.02em, uppercase): day headers in the history list ("HÔM NAY").
- **Footnote** (400, 13px, 1.4): the honesty note under the info sheet list; the count badge uses 13px/700. In the wide panel 13px also sets the centred drop/paste note, the empty-history note and the people rows' percentage line.
- **Verdict Title** (700, 26px, 1.2, -0.01em): the wide panel's full-sentence verdict ("1 người không đội mũ", "Tất cả đội mũ") or, before any result, the mode title ("Chưa có ảnh", "Camera đang tắt"); summary line below in 15px secondary.
- **Segment Label** (500, 15px; 600 when selected): the panel's segmented control, sentence case ("Ảnh", "Video", "Trực tiếp").
- **Caption** (400, 12px): the time under each recent-history crop.
- The desktop drop zone title uses 22px/600 (the empty-state size), with a 15px secondary line capped at 60ch.

### Named Rules
**The Platform Voice Rule.** Uppercase exists only where iOS uses it: the camera mode row and grouped-list section headers. No other label is uppercased or letter-spaced.

## Layout

The app fills the viewport (100dvh, no width cap); layout is chosen by two independent tests.

**Device rule.** A device with no touch screen (`navigator.maxTouchPoints === 0`) is a desktop: the modes are ẢNH and VIDEO only, the default is ẢNH, and image or video files can be dropped anywhere on the camera screen or pasted (⌘V on Apple platforms, Ctrl+V elsewhere); a dropped or pasted file switches to the matching mode. Touch devices (iPhone, iPad) keep all three modes and open on TRỰC TIẾP. The user agent is never used for this, because iPadOS Safari reports itself as a Mac.

**Width rule.** `(min-width: 900px) and (orientation: landscape)` (desktop, iPad landscape) switches the camera screen to two columns: the viewfinder (`minmax(0, 1fr)`, 24px inner padding) on the left and the dark panel (`clamp(340px, 28vw, 400px)`) on the right. The panel is a scrolling flex column with a 12px gap, 24px sides, safe-area top + 16px and bottom + 24px; its children never shrink. Narrower or portrait viewports (iPhone, iPad portrait) use the phone layout below at full width.

**Phone layout.** The camera screen is a vertical flex: the viewfinder takes all remaining height and the controls bar sits below it. The viewfinder is a size container; the stage inside is sized by aspect ratio (`min(100cqw, 100cqh × ar)`) so photo, video and camera are letterboxed in black and detection boxes are positioned in percent of the image, always aligned.

Floating chrome sits on the viewfinder in a top bar (safe-area top + 8px, 12px sides): a 44px spacer, the centred verdict capsule, the 44px info button. The controls bar (12px top, 24px sides, safe-area bottom + 16px) holds the mode row (20px gap, 14px below) and a three-column row (1fr auto 1fr): thumbnail left, shutter centre, round button right; a 52px spacer keeps the shutter centred when a slot is empty.

Non-camera screens use 16px page gutters with iOS grouped insets: section headers 22px above / 7px below, groups 20px radius, separators inset 16px (84px in the history list so they start after the crop). Sheets rise from the bottom, full width up to 480px. On wide screens the history list is centred: side padding is `max(16px, (100% − 680px) / 2)`, so the grouped list never runs wider than 680px; the black detail screen stays full width. All edges respect `env(safe-area-inset-*)`. Every interactive target is at least 44px; detection boxes extend their hit area to at least 44px with an invisible overlay.

## Elevation & Depth

Flat iOS surfaces; depth comes from blur and from rings, not from cast shadows. Anything floating over the image uses glass (black at 60%, `blur(20px) saturate(1.6)`; 60% keeps white text ≈ 5.7:1 over sky or white walls). The only soft shadows are small and sit on elements over an unpredictable photo: badges and the confidence tag.

### Shadow Vocabulary
- **Badge ring** (`box-shadow: 0 0 0 2px #fff, 0 1px 4px rgba(0,0,0,0.35)`): white ring plus a short lift so "!" and ✓ read on any background.
- **Tag lift** (`box-shadow: 0 2px 8px rgba(0,0,0,0.3)`): confidence tag over the image.
- **Count cut-out** (`box-shadow: 0 0 0 2px #000`): separates the count badge from the thumbnail.
- **Thumb hairline** (`box-shadow: inset 0 0 0 1px rgba(255,255,255,0.22)`): edge of the thumbnail on black.
- **Crop ring** (`box-shadow: inset 0 0 0 2px` violation orange): history row crops, marking them as violations.
- **Hint shadow** (`text-shadow: 0 1px 8px rgba(0,0,0,0.6)`): the empty-viewfinder hint line.
- **Segment lift** (`box-shadow: 0 2px 6px rgba(0,0,0,0.25)`): the selected segment in the panel's segmented control.
- **Notice lift** (`box-shadow: 0 4px 16px rgba(0,0,0,0.35)`): the error notice floating at the bottom of the viewfinder.
- **Panel crop ring** (`outline: 2px solid` violation orange, offset −2px): people-list crops, the panel counterpart of the crop ring.

The wide panel itself is tonal, not lifted: panel-bg beside the black viewfinder, panel-cell groups on panel-bg, no shadow between them.

### Named Rules
**The Glass Over Image Rule.** Chrome that floats on the viewfinder is glass with backdrop blur; it is never an opaque card.

## Shapes

Circles for camera controls (shutter, glass button, round button, badges, verdict dot), continuous capsules for the verdict and tags, and gently rounded rectangles for content: detection boxes 6px, thumbnail 10px, history crops 12px, grouped lists 20px, sheets 28px on the top corners only. The wide panel adds full pills for its buttons (25px on 50px), a capsule segmented control (18px track, 15px segments), 14px grouped lists and error notice, 10px people crops and mini badges, 12px recent-history crops, and a 24px dashed drop zone. The shutter's inner disc (62px) morphs into a 30px rounded square (7px) when running, like the Camera app's record button.

## Components

### Shutter
Camera-app record control. 78px circle with a 4px white ring and a 62px inner disc.
- **pick** (photo, finished video): white disc; opens the file picker.
- **rec** (live camera off, video ready or paused): red disc.
- **stop** (camera running, video playing): red 30px rounded square; morphs over 260ms with the standard ease.
- **Active:** inner shape scales to 0.9 (120ms). **Disabled:** 50% opacity (while the camera is opening).

### Mode Row
Phone layout only (the wide panel uses the segmented control). Three text buttons, 13px/600 uppercase, white at 82%, 44px tall, 20px apart; the active mode (`aria-pressed`) turns mode yellow. On a desktop narrower than the wide breakpoint the row shows only ẢNH and VIDEO. Switching mode remounts the mode (camera off, video stopped, tracker reset).

### Last-Violation Thumbnail
52px rounded square (10px) on #1c1c1e showing a square crop of the newest violator, cut from the saved image by background-position. The unseen count sits top-right in a violation-ink 22px pill with a black cut-out ring. With motion allowed, a new crop pops in (scale 0.4 → 1.12 → 1, 420ms). Empty: a stack glyph at 65% white. Opens the history.

### Glass Button and Round Button
- **Glass:** 44px circle, glass background, white 24px glyph (info).
- **Round:** 52px circle, white at 14%, white 26px glyph (switch camera in live mode, clear file in photo/video).

### Verdict Capsule
Glass capsule, min 40px tall, 20px radius, 12px dot + 17px/600 text, `aria-live="polite"`. States: orange dot + "N vi phạm không đội mũ" (only tracker-confirmed violators in video and camera); white-55% dot + "Đang xác nhận…" while a newly flagged person is not yet confirmed; green dot with a faint white ring + "Tất cả đội mũ"; white-55% dot + "Không thấy người". Reused centred under the image on the history detail screen. On the wide layout it stays on the viewfinder (a 44px spacer replaces the info button, which moves to the panel header), and the panel repeats the verdict in a full sentence.

### Detection Box (signature)
Boxes are buttons placed in percent of the image, 6px radius.
- **Violator:** 3px violation-orange stroke, orange fill at 28% (`rgba(226, 84, 27, 0.28)`), "!" badge.
- **Helmet:** 2px helmet-green stroke, no fill, ✓ badge.
- **Badge:** 24px circle in the signal colour, white 2px ring, white glyph (16px "!" / 15px ✓, 3px stroke). Default position centred on the box's top-left corner; for boxes shorter than 72px on screen (3 × badge) it moves above the box, centred, 4px clear of the top edge, so it never covers a small person's head. Positions are clamped 2px inside the image.
- **Stacking:** violators are placed first. A "!" that collides with an earlier badge (within 26px on both axes) moves up exactly one step (26px) and stays with its person. A ✓ that would collide with any badge is dropped; the green outline still marks the person. Boxes create no stacking context; z-order is ✓ badge (3) < "!" badge (4) < tag (5), so every badge sits above every orange fill.
- **Tap:** the box toggles a confidence tag ("Không đội mũ · 87%" / "Đội mũ · 92%", 15px/600 white on the ink variant of the signal colour, 13px radius) 6px above its badge; the other boxes dim to 30% opacity (200ms). Near the top edge the tag goes below the box; near the right edge it aligns right. Tapping empty image clears the focus. On the wide layout the focused person is shared with the panel's people list: selecting a violator row focuses that box, and tapping a violator box highlights its row (helmet wearers share one static row).
- **Motion:** on a still result (photo, history detail) boxes ink in (opacity 0 and scale 1.06 → 1, 360ms). Live camera and video update per frame without animation.

### Metrics Bar (phone, portrait iPad)
Glass capsule (same material as the verdict capsule, 16px radius, 7px 14px padding) centred 12px above the viewfinder bottom, one line of 15px/500 tabular white items 14px apart (14px and 10px apart in a viewfinder ≤ 380px), z-index 6 above box badges and tags, each a 17px glyph plus text: "2 người" (person; far people as "3 người +1 xa", the item that truncates first), "Lệch 42°" (compass; "Lệch –" before the first saved image or without a motion sensor), "287 ms" (timer). Photo and video show people and time only. Not interactive; never wider than the viewfinder minus 24px. The error notice moves up to 64px while the bar is shown.

### Wide Panel (≥ 900px landscape)
Dark iOS side column beside the viewfinder (panel-bg, white text, secondary label-secondary-dark, tint tint-dark). Top to bottom:
- **Header:** "HelmetCheck" in 17px bold (browser `<b>` weight, 700) left, a plain 44px info button right (white glyph, no fill).
- **Segmented control:** iOS segmented control with the device's modes (ẢNH/VIDEO on desktop, three on iPad); 3px track inset, 38px segments, the selected one segment-selected with the segment lift and 600 weight; background change 200ms.
- **Verdict:** 14px signal dot plus the full sentence in Verdict Title. Below it, the same three numbers as the phone metrics bar as a row of equal tiles (panel-cell, 14px radius, 10px 12px padding, 8px gap): the value in 22px/700 on top, the label in 13px secondary under it ("người", "lệch hướng", "ms mỗi khung", or "ms xử lý ảnh" for a photo; the time tile shows the bare number so a slow device's "1024" still fits one line); the heading tile only in live camera. Without a result the dot and tiles are omitted and the mode title and hint stand in. `aria-live="polite"`.
- **Buttons:** full-width 50px pills, 17px/600 white text after a 24px icon: primary (tint-dark) for the shutter's action ("Chọn ảnh", "Phát và phân tích", "Mở camera"), danger (record red) while running ("Tạm dừng", "Tắt camera"), gray (gray-fill) for the secondary action ("Bỏ ảnh này", "Bỏ video này", "Đổi camera trước / sau"). Disabled at 50% opacity. On desktop with media loaded and nothing running, a centred 13px note follows: "hoặc kéo thả, dán (⌘V) ảnh / video khác vào trang".
- **People list** ("NGƯỜI PHÁT HIỆN" section header, only when people are found): a dark grouped list (panel-cell, 14px radius, separators inset 64px). Up to 5 violator rows in stable tracker order; each row is a 60px button with a 40px crop of that person (from the photo, or redrawn from the current video/camera frame) ringed in violation orange, falling back to a violation-ink mini badge with "!" when no crop source exists; title "Không đội mũ" in violation-text-dark, confidence below in 13px. A selected person outside the first five replaces the fifth row. Beyond five, one static row "và N người không đội mũ khác" / "xem khung trên ảnh". Helmet wearers collapse into one static row: helmet-ink mini badge with ✓, "N người đội mũ" in white, confidence range ("86%–94%") below. The selected row takes the focus wash.
- **Recent history** ("LỊCH SỬ GẦN ĐÂY" header with a tint "Xem tất cả" link): a four-column grid of square crops (12px radius, gray-fill placeholder, orange inset crop ring) with the 12px time underneath; each opens that record's detail.

### Drop Zone (desktop)
Shown in the empty viewfinder in ẢNH and VIDEO on a desktop: a button inset 24px with a 2px dashed white-30% border and 24px radius, centred 72px circle (white 10%) holding the upload glyph, title "Kéo thả ảnh hoặc video công trường vào đây" (22px/600), and a 15px secondary line "Ảnh JPG, PNG, WebP · video MP4, WebM · hoặc bấm để chọn tệp · mô hình chạy ngay trên máy, không gửi đi đâu" (replaced by the model loading status while it loads). Clicking opens the file picker. While a file is dragged over the screen, a 3px dashed tint-dark outline with a 10% tint wash appears 16px inside the viewfinder.

### Error Notice
A short alert ("Không mở được tệp này. Hãy dùng ảnh JPG, PNG hoặc video MP4.") for an unreadable file: centred 20px above the viewfinder bottom (48px inside the drop zone), max `min(90%, 520px)`, 10px 16px padding, 14px radius, 15px/600 white text, notice lift, `role="alert"`; hides after 5s or when a new file is taken. Its fill is gray-fill (#3a3a3c), a neutral system surface, so a file error is never mistaken for a no-hard-hat mark (Two Signals Rule).

### Hover (pointer devices)
Only under `(hover: hover)`: panel buttons brighten (`brightness(1.12)`); unselected segments darken to the track at 32%; people rows and recent crops take a white-6% wash; plain, glass and round buttons a white-18% fill; text links and "Xong" drop to 70% opacity; the drop zone border rises to white 55%; history rows take the fill colour. Touch devices get no hover styling.

### Info Sheet
Bottom sheet on a 40% black backdrop, grouped-bg surface, 28px top radius, rises in 360ms (backdrop fades 240ms). Header: 20px/700 title left, "Xong" tint text button right. Content: one grouped list of key/value rows (value in secondary label, right-aligned, tabular figures) and a 13px footnote stating the model's limits. Escape and backdrop tap close it.

### Grouped List and History Row
iOS inset grouped list: cell background, 20px radius, rows min 48px with 16px padding, 0.5px separators inset from the leading edge. History rows are full-width buttons (min 76px): 56px crop with orange inset ring, bold title "N không đội mũ", 15px secondary line "14:47 · Camera", tint unread dot (10px), separator-coloured chevron. A separate group holds the centred red "Xóa tất cả" (52px) with a confirm dialog.

### Navigation
No tab bar. Camera is home; the thumbnail opens History (large title "Lịch sử", subtitle "Lưu trên máy này", sticky nav bar with "‹ Màn hình chính"). A row opens the black Detail screen: back link "‹ Lịch sử" (or "‹ Màn hình chính" when the record was opened from the panel's recent-history grid, returning straight to the camera screen) and a red trash button in a static dark nav bar, image letterboxed, verdict capsule and meta line below. When the record has violators, phones and iPad portrait add a primary "Xem chi tiết N người" button under the meta line; it pushes a black screen (back link "‹ Ảnh vi phạm", 28px bold verdict, source and time) with one tile per violator in two columns (one wider tile for a single violator), left to right, each cropped to the saved box plus a small margin and marked with the "!" badge on the photo. The tile ratio follows the people in that record (tall for standing people, near square for close-ups) so rows stay even without large empty areas. In phone landscape the photo keeps the height, with verdict and button side by side, and tiles shrink so one person fits on screen. In the wide layout (≥ 900px landscape) the same tiles sit in the right panel with no button. Crops are read from the saved image and boxes only. Focus is a 3px tint outline offset 2px.

### Empty States
Camera: the black viewfinder with one centred hint line ("Chọn một video công trường để kiểm tra") or the model loading status. Wide panel: the mode title as the verdict ("Chưa có ảnh") with the hint below, and "Chưa có vi phạm nào được lưu trên máy này." in place of the recent grid. History: 72px fill-coloured circle with a stack glyph, 22px/700 "Chưa có vi phạm", one secondary sentence capped at 30ch.

## Do's and Don'ts

### Do:
- **Do** use the system font stack at the iOS sizes (34 / 20 / 17 / 15 / 13, plus 26 and 12 in the wide panel); weight, not typeface, carries hierarchy.
- **Do** keep orange for no hard hat and green for hard hat, each paired with "!" / ✓ or words.
- **Do** float chrome over the image as glass (black 60%, blur 20px, saturate 1.6) in circles or capsules.
- **Do** keep every target at least 44px, including small detection boxes (invisible 44px hit area).
- **Do** letterbox media in black and position boxes in percent of the image.
- **Do** give every grouped-list colour a dark-appearance pair; the camera and detail screens stay black in both.
- **Do** tell devices apart by capability (`navigator.maxTouchPoints`, the `(min-width: 900px) and (orientation: landscape)` query), never by user agent.
- **Do** keep the wide panel in dark iOS material in both appearances and let it repeat the verdict in words; the viewfinder keeps only the capsule.
- **Do** use the standard ease `cubic-bezier(0.16, 1, 0.3, 1)`, gate entrance animation behind `prefers-reduced-motion: no-preference`, and switch state transitions (shutter morph, box dimming) off under `reduce`.

### Don't:
- **Don't** put statistics, model names or timings on the camera screen; they belong in the info sheet.
- **Don't** use orange or green for anything that is not a detection verdict, and don't use record red for detections.
- **Don't** let a ✓ badge drift onto another person; drop it and rely on the green outline.
- **Don't** set small white text on violation orange or helmet green (white on these hues is about 3.8:1); use violation-ink / helmet-ink.
- **Don't** offer TRỰC TIẾP on a device without a touch screen.
- **Don't** use violation orange or its ink for errors or system notices; the error notice uses gray-fill.
- **Don't** reintroduce drafting-sheet devices from the replaced world: title blocks, condensed display type, grid paper, numbered callout bubbles.
