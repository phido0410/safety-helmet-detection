# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React + Vite (chosen by the user), plain CSS, no UI framework. Static build deployed to Vercel. The model runs in the browser
with onnxruntime-web 1.30.0 (WASM; WebGPU was slower on the iPhone 11); pre/post-processing lives in `demo/detector.js` and is tested against
Ultralytics (`node demo/test/run.mjs`).

## Users

Two audiences, one product (confirmed by the user):

- **Site safety supervisor** on a Vietnamese construction site, phone in one hand, often outdoors in strong sunlight, checking
  whether workers wear hard hats. Needs the answer at a glance and a record of violations.
- **Thesis committee and supervisor (GVHD)** watching the student demonstrate the graduation project (ĐATN) on an iPhone. They
  need to see clearly what the model detected and trust the result.

## Product Purpose

HelmetCheck detects people on a construction site and flags those not wearing a hard hat, from a photo, a video or the live
phone camera. It automatically saves a snapshot of each person without a hard hat as a violation history. It is the demo
program of the thesis "Xây dựng mô hình học sâu phát hiện người và giám sát tuân thủ đội mũ bảo hộ lao động tại công trường
xây dựng" (Đỗ Ngọc Phi, HUMG, 2026). Success: the committee can watch it run on a real phone, offline, and see correct results.

## Positioning

The detection model runs entirely on the phone: no image leaves the device and no server is needed. The model (M3b, YOLO26n
fine-tuned) was trained to tell hard hats apart from ordinary Vietnamese headwear (nón lá, mũ vải, mũ lưỡi trai, mũ cối), which a
model trained only on the public dataset gets wrong, and with background images so that scenes without people (a desk, a laptop) are
not reported as a person.

## Operating Context

- Device: iPhone 11 Pro Max, Safari, installed with "Thêm vào Màn hình chính" (standalone PWA). Speed on the device is being
  measured (`demo/bench.html`); camera processing rate depends on that result.
- Inputs: photo from library or camera, video file, live camera.
- Classes the model outputs: helmet, head, head_with_helmet, person_with_helmet, person_no_helmet, face. The violation class is
  person_no_helmet (threshold 0.213, chosen on the validation set so the 95% lower bound of recall ≥ 0.80); other classes use
  0.399.

## Capabilities and Constraints

- All UI copy in Vietnamese. App name on the home screen: **HelmetCheck**.
- Violation history is stored only on the device (no backend, no account).
- Known model limits that the UI must not hide or overstate: small/distant people are often missed; about 12–24% of people
  wearing a hard hat are falsely flagged on Vietnamese site photos (thesis week 9); 6.5% of person-free photos still get a false
  "no hard hat" box, mostly close-up animal faces (thesis week 10). The result is an aid, not a verdict.
- Licenses to show when published: Ultralytics (AGPL-3.0), SH17 labels (CC BY-NC-SA 4.0), Open Images V7 (CC BY 4.0).
- Publishing to Vercel requires the user's go-ahead each time.

## Brand Commitments

Name: HelmetCheck. Brand mark (user-approved 2026-11-06): a glossy black three-quarter hard hat with a yellow ✓ sticker on safety yellow `#ffd60a`, drawn by hand as SVG (`demo/public/icons/hat.svg`), used for the intro screen and the app icon. Report figures use green `#1baf7a` for "đội mũ" and orange `#eb6834` for
"không đội mũ"; the app keeps that green/orange pairing (same meaning, same hues) but uses darker values (`#14945f`,
`#e2541b`) for contrast in outdoor sunlight. The app follows iOS conventions (system font, Camera-app layout), chosen by the
user on 2026-11-03 from a Figma sketch board after the earlier "Bản vẽ thi công" direction proved hard to read on the phone.

## Evidence on Hand

Real model metrics in `reports/` (test SHEL5K mAP@0.5 0.907; out-of-domain 0.702–0.820; Core ML FP16 18.4 ms on MacBook Air M1).
News photos used for evaluation are copyrighted and must not appear in the app, the repo or screenshots that get published.
No testimonials, users or deployment claims exist; do not invent any.

## Product Principles

1. Answer first: whether anyone is not wearing a hard hat must be readable in under a second, in sunlight, at arm's length.
2. Honest output: show what the model saw (boxes, confidence) and never present a detection as certain.
3. Private by construction: everything stays on the phone.
4. Works on the real device: performance budgets come from measurements on the iPhone, not assumptions.

## Accessibility & Inclusion

Outdoor use in bright light: high contrast, large touch targets (one-handed, possibly with gloves). Violation state must not
rely on color alone (icon and text as well).
