// Builds Edgerunners-Pitch.pptx: the Guardian design, a halo that travels between slides with Morph,
// and clickable buttons that branch into three demo calls.
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const sharp = require("sharp");
const JSZip = require("jszip");
const md = require("react-icons/md");
const { applyTheme } = require("C:/Users/OMEN/AppData/Local/Claude-Data/claude_pzs8sxrjxfjjc/local-agent-mode-sessions/skills-plugin/fc66c114-7001-4eeb-8421-c70f5620cd5f/f2c4dc56-9673-4ca2-99cb-079380614abf/skills/pptx/scripts/apply_theme.js");

const OUT = path.join(__dirname, "Edgerunners-Pitch.pptx");
const W = 13.333, H = 7.5;
const FONT = "Segoe UI";

const K = {
  night: "0E1A27", night2: "0A131D", bezel: "2E4257", raised: "1B3550",
  ink: "1F2937", slate: "4B5563", paper: "FAFAF8", white: "FFFFFF", line: "E6E8EB",
  blue: "226192", blueDark: "123A58", mist: "E3EDF5", haloBlue: "7DB8E8", muted: "A9B6C3",
  amber: "F5B83D", amberCore: "3A2A08", amberText: "FFD98A", amberDeep: "F2B035", onAmber: "2B1D00",
  red: "8F1D16", redBright: "D92D20", grey: "C9CDD3", greyCore: "E6E8EB", pink: "FBE3E1", amberSoft: "FFF4DC",
};

const THEME = {
  name: "Edgerunners Guardian",
  headFontFace: FONT,
  bodyFontFace: FONT,
  colors: {
    dk1: K.ink, lt1: K.white, dk2: K.night, lt2: K.paper,
    accent1: K.blue, accent2: K.haloBlue, accent3: K.amber, accent4: K.red, accent5: K.mist, accent6: "F4BEBB",
    hlink: K.blue, folHlink: K.blueDark,
  },
};

// ---------- icons ----------
const iconCache = {};
async function icon(name, hex) {
  const key = name + hex;
  if (!iconCache[key]) {
    const svg = renderToStaticMarkup(React.createElement(md[name], { size: 256, color: "#" + hex }));
    const png = await sharp(Buffer.from(svg)).resize(256, 256).png().toBuffer();
    iconCache[key] = "image/png;base64," + png.toString("base64");
  }
  return iconCache[key];
}
let HOT;

// Slide numbers, fixed up front so buttons can link forward.
const S = {
  title: 1, scam: 2, trick: 3, today: 4, question: 5, menu: 6,
  qrRing: 7, qrListen: 8, qrCheck: 9, qrAlert: 10, qrStory: 11,
  otpCheck: 12, otpAlert: 13, calmListen: 14, calmStory: 15,
  how: 16, rules: 17, next: 18, close: 19,
};

// ---------- building blocks ----------
function txt(slide, text, o) {
  slide.addText(text, Object.assign({ isTextBox: true, margin: 0, fontFace: FONT, valign: "top" }, o));
}

// Invisible click target: in slide show, clicking it jumps to `to`.
function hotspot(slide, x, y, w, h, to, tooltip) {
  slide.addImage({ data: HOT, x, y, w, h, hyperlink: { slide: to, tooltip }, objectName: "hot-" + tooltip, altText: tooltip });
}

const HALO = {
  watch: { ring: K.blue, t: [82, 64, 40], core: K.blue, icon: ["MdOutlineShield", K.white] },
  listen: { ring: K.haloBlue, t: [80, 62, 38], core: K.raised, icon: ["MdPersonOutline", "E8F1F9"] },
  ring: { ring: K.haloBlue, t: [66, 44, 20], core: K.raised, icon: ["MdPersonOutline", "E8F1F9"] },
  shieldNight: { ring: K.haloBlue, t: [80, 62, 38], core: K.raised, icon: ["MdOutlineShield", "E8F1F9"] },
  check: { ring: K.amber, t: [70, 42, 10], core: K.amberCore, icon: ["MdWarningAmber", K.amberText] },
  faint: { ring: K.haloBlue, t: [88, 80, 66], core: "16283A", icon: ["MdOutlineShield", "2A3F55"] },
};

// The halo: three rings and a core, named with "!!" so Morph treats them as the same objects on every slide.
async function halo(slide, cx, cy, d, state) {
  const s = HALO[state];
  const rings = [[2.75, "!!halo-r3", s.t[0]], [2.1, "!!halo-r2", s.t[1]], [1.5, "!!halo-r1", s.t[2]]];
  for (const [k, name, t] of rings) {
    const rd = d * k;
    slide.addShape("ellipse", {
      x: cx - rd / 2, y: cy - rd / 2, w: rd, h: rd, objectName: name,
      fill: { color: s.ring, transparency: 100 }, line: { color: s.ring, width: Math.max(1, d * 2.2), transparency: t },
    });
  }
  slide.addShape("ellipse", { x: cx - d / 2, y: cy - d / 2, w: d, h: d, objectName: "!!halo-core", fill: { color: s.core }, line: { color: s.core, width: 0 } });
  const id = d * 0.52;
  slide.addImage({ data: await icon(s.icon[0], s.icon[1]), x: cx - id / 2, y: cy - id / 2, w: id, h: id, objectName: "!!halo-icon", altText: "Scam check" });
}

// The halo blown up to fill the slide: Morph grows it out of the phone as the alert.
function haloAlert(slide, fill) {
  const d = 16.5, cx = W / 2, cy = H / 2;
  [[22, "!!halo-r3"], [19.5, "!!halo-r2"], [17.6, "!!halo-r1"]].forEach(([rd, name]) => {
    slide.addShape("ellipse", { x: cx - rd / 2, y: cy - rd / 2, w: rd, h: rd, objectName: name, fill: { color: fill, transparency: 100 }, line: { color: fill, width: 1, transparency: 100 } });
  });
  slide.addShape("ellipse", { x: cx - d / 2, y: cy - d / 2, w: d, h: d, objectName: "!!halo-core", fill: { color: fill }, line: { color: fill, width: 0 } });
}

// Phone frame and screen. Same names on every slide so the phone stays put while its screen changes.
const P = { x: 8.75, y: 0.45, w: 3.3, h: 6.6 };
const PC = P.x + P.w / 2; // 10.4
function phone(slide, screen) {
  slide.addShape("roundRect", { x: P.x, y: P.y, w: P.w, h: P.h, rectRadius: 0.48, objectName: "!!phone", fill: { color: K.night2 }, line: { color: K.bezel, width: 1.5 } });
  slide.addShape("roundRect", { x: P.x + 0.1, y: P.y + 0.1, w: P.w - 0.2, h: P.h - 0.2, rectRadius: 0.4, objectName: "!!screen", fill: { color: screen === "light" ? K.paper : K.night }, line: { color: screen === "light" ? K.paper : K.night, width: 0 } });
}

function pill(slide, text, x, y, w, h, fill, color, name, size = 11, bold = true) {
  txt(slide, text, { shape: "roundRect", rectRadius: h / 2, x, y, w, h, fill: { color: fill }, color, fontSize: size, bold, align: "center", valign: "middle", objectName: name });
}

async function roundButton(slide, cx, cy, d, fill, iconName, label, name) {
  slide.addShape("ellipse", { x: cx - d / 2, y: cy - d / 2, w: d, h: d, objectName: name, fill: { color: fill.bg, transparency: fill.t || 0 }, line: { color: fill.line || fill.bg, width: fill.line ? 1 : 0 } });
  const s = d * 0.45;
  slide.addImage({ data: await icon(iconName, fill.fg), x: cx - s / 2, y: cy - s / 2, w: s, h: s, objectName: name + "-icon", altText: label });
  txt(slide, label, { x: cx - 0.6, y: cy + d / 2 + 0.06, w: 1.2, h: 0.25, fontSize: 10, color: K.muted, align: "center", objectName: name + "-label" });
}

// Narration down the left of the demo slides.
function step(slide, num, title, body, hint) {
  txt(slide, num, { x: 0.8, y: 1.55, w: 7, h: 0.4, fontSize: 14, bold: true, color: K.haloBlue, charSpacing: 2, objectName: "!!step-num" });
  txt(slide, title, { x: 0.8, y: 2.0, w: 7.2, h: 1.9, fontSize: 38, bold: true, color: K.white, objectName: "!!step-title", valign: "top" });
  const by = title.length > 26 ? 3.95 : 3.05;
  txt(slide, body, { x: 0.8, y: by, w: 6.8, h: 1.3, fontSize: 18, color: K.muted, objectName: "!!step-body" });
  if (hint) txt(slide, hint, { x: 0.8, y: 6.45, w: 7, h: 0.35, fontSize: 13, italic: true, color: K.haloBlue, objectName: "!!step-hint" });
}

// ---------- phone screens ----------
async function screenHome(slide) {
  phone(slide, "light");
  slide.addImage({ data: await icon("MdOutlineShield", K.blue), x: P.x + 0.35, y: 0.82, w: 0.24, h: 0.24, objectName: "!!p-brand-icon" });
  txt(slide, "Edgerunners", { x: P.x + 0.65, y: 0.8, w: 2, h: 0.3, fontSize: 12, bold: true, color: K.blue, objectName: "!!p-top" });
  await halo(slide, PC, 2.3, 0.82, "watch");
  txt(slide, "Watching your calls", { x: P.x + 0.2, y: 3.62, w: P.w - 0.4, h: 0.4, fontSize: 16, bold: true, color: K.ink, align: "center", objectName: "!!p-title" });
  txt(slide, "If a caller asks for a QR scan, UPI PIN or OTP, you'll know in seconds.", { x: P.x + 0.3, y: 4.05, w: P.w - 0.6, h: 0.6, fontSize: 10, color: K.slate, align: "center", objectName: "!!p-sub" });
  slide.addShape("roundRect", { x: P.x + 0.3, y: 4.85, w: P.w - 0.6, h: 0.72, rectRadius: 0.14, objectName: "!!p-card", fill: { color: K.white }, line: { color: K.line, width: 0.75 } });
  txt(slide, "Scam check", { x: P.x + 0.48, y: 4.95, w: 1.8, h: 0.26, fontSize: 11, bold: true, color: K.ink, objectName: "!!p-card-title" });
  txt(slide, "On for every call", { x: P.x + 0.48, y: 5.22, w: 1.8, h: 0.24, fontSize: 9, color: K.slate, objectName: "!!p-card-sub" });
  slide.addShape("roundRect", { x: P.x + 2.25, y: 5.06, w: 0.56, h: 0.32, rectRadius: 0.16, objectName: "!!p-switch", fill: { color: K.blue }, line: { color: K.blue, width: 0 } });
  slide.addShape("ellipse", { x: P.x + 2.51, y: 5.09, w: 0.26, h: 0.26, objectName: "!!p-knob", fill: { color: K.white }, line: { color: K.white, width: 0 } });
  slide.addShape("roundRect", { x: P.x + 0.3, y: 5.8, w: P.w - 0.6, h: 0.46, rectRadius: 0.12, objectName: "!!p-lang", fill: { color: K.line }, line: { color: K.line, width: 0 } });
  pill(slide, "English", P.x + 0.36, 5.85, 0.86, 0.36, K.white, K.blue, "!!p-lang-1", 9);
  txt(slide, "हिन्दी", { x: P.x + 1.24, y: 5.85, w: 0.86, h: 0.36, fontSize: 9, bold: true, color: K.slate, align: "center", valign: "middle", objectName: "!!p-lang-2" });
  txt(slide, "ਪੰਜਾਬੀ", { x: P.x + 2.1, y: 5.85, w: 0.86, h: 0.36, fontSize: 9, bold: true, color: K.slate, align: "center", valign: "middle", objectName: "!!p-lang-3" });
}

async function screenIncoming(slide) {
  phone(slide, "night");
  txt(slide, "Incoming call", { x: P.x + 0.2, y: 0.82, w: P.w - 0.4, h: 0.3, fontSize: 11, color: K.muted, align: "center", objectName: "!!p-top" });
  await halo(slide, PC, 2.5, 0.95, "ring");
  txt(slide, "Unknown number", { x: P.x + 0.2, y: 3.95, w: P.w - 0.4, h: 0.42, fontSize: 17, bold: true, color: K.white, align: "center", objectName: "!!p-title" });
  txt(slide, "+91 98XXX XXX21", { x: P.x + 0.2, y: 4.38, w: P.w - 0.4, h: 0.3, fontSize: 11, color: K.muted, align: "center", objectName: "!!p-sub" });
  pill(slide, "Scam check will listen with you", P.x + 0.35, 4.85, P.w - 0.7, 0.38, "21384F", "CFE4F6", "!!p-card", 9);
  await roundButton(slide, P.x + 0.95, 6.0, 0.72, { bg: K.redBright, fg: K.white }, "MdCallEnd", "Decline", "!!p-btn-a");
  await roundButton(slide, P.x + P.w - 0.95, 6.0, 0.72, { bg: "2E7BC0", fg: K.white }, "MdCall", "Answer", "!!p-btn-c");
}

async function screenCall(slide, mode, clock, chip) {
  phone(slide, "night");
  txt(slide, "Unknown number", { x: P.x + 0.2, y: 0.78, w: P.w - 0.4, h: 0.34, fontSize: 14, bold: true, color: K.white, align: "center", objectName: "!!p-top" });
  txt(slide, clock, { x: P.x + 0.2, y: 1.1, w: P.w - 0.4, h: 0.26, fontSize: 10, color: K.muted, align: "center", objectName: "!!p-clock" });
  await halo(slide, PC, 2.55, 0.9, mode === "check" ? "check" : "listen");
  const card = mode === "check"
    ? { bg: "2A2412", line: K.amber, title: "Checking a payment request…", sub: "Don't scan, pay or share anything yet.", fg: "FFE3A6" }
    : { bg: "16283A", line: "2F4A63", title: "Listening with you", sub: "We'll warn you if they ask for a QR scan, UPI PIN or OTP.", fg: "E8F1F9" };
  slide.addShape("roundRect", { x: P.x + 0.25, y: 3.95, w: P.w - 0.5, h: 1.45, rectRadius: 0.16, objectName: "!!p-card", fill: { color: card.bg }, line: { color: card.line, width: 1.25 } });
  txt(slide, card.title, { x: P.x + 0.42, y: 4.07, w: P.w - 0.84, h: 0.3, fontSize: 12, bold: true, color: card.fg, objectName: "!!p-card-title" });
  txt(slide, card.sub, { x: P.x + 0.42, y: 4.4, w: P.w - 0.84, h: 0.46, fontSize: 9.5, color: card.fg, objectName: "!!p-card-sub" });
  if (chip) pill(slide, "Heard: " + chip, P.x + 0.42, 4.93, P.w - 0.84, 0.32, K.amber, K.onAmber, "!!p-chip", 9);
  const ctl = { bg: K.white, t: 92, fg: "F3F5F7", line: "3A4E63" };
  await roundButton(slide, P.x + 0.75, 6.0, 0.62, ctl, "MdMicOff", "Mute", "!!p-btn-a");
  await roundButton(slide, PC, 6.0, 0.62, ctl, "MdVolumeUp", "Speaker", "!!p-btn-b");
  await roundButton(slide, P.x + P.w - 0.75, 6.0, 0.62, { bg: K.redBright, fg: K.white }, "MdCallEnd", "End", "!!p-btn-c");
}

// Full-screen alert grown out of the halo.
async function alertSlide(slide, a) {
  haloAlert(slide, K.red);
  slide.addImage({ data: await icon("MdWarningAmber", K.white), x: 0.8, y: 0.62, w: 0.42, h: 0.42, objectName: "al-icon" });
  txt(slide, "HIGH RISK", { x: 1.32, y: 0.66, w: 3, h: 0.36, fontSize: 16, bold: true, color: K.white, charSpacing: 3, objectName: "al-level" });
  txt(slide, "Automatic check", { x: 3.2, y: 0.69, w: 3, h: 0.32, fontSize: 13, color: "F6CFCB", objectName: "al-auto" });
  txt(slide, a.title, { x: 0.8, y: 1.35, w: 7.6, h: 1.9, fontSize: 36, bold: true, color: K.white, objectName: "al-title" });
  slide.addShape("roundRect", { x: 0.8, y: 3.45, w: 7.4, h: 1.38, rectRadius: 0.2, objectName: "al-truth-bg", fill: { color: K.white, transparency: 88 }, line: { color: K.white, width: 0, transparency: 100 } });
  txt(slide, "THE TRUTH", { x: 1.1, y: 3.62, w: 5, h: 0.3, fontSize: 12, bold: true, color: "F6CFCB", charSpacing: 3, objectName: "al-truth-label" });
  txt(slide, a.truth, { x: 1.1, y: 3.95, w: 6.9, h: 0.8, fontSize: 18, color: K.white, objectName: "al-truth" });
  txt(slide, "DO THIS NOW", { x: 0.8, y: 5.1, w: 5, h: 0.3, fontSize: 12, bold: true, color: "F6CFCB", charSpacing: 3, objectName: "al-next-label" });
  txt(slide, a.next, { x: 0.8, y: 5.42, w: 7.9, h: 0.7, fontSize: 20, bold: true, color: K.white, objectName: "al-next" });
  slide.addImage({ data: await icon("MdRecordVoiceOver", "F6CFCB"), x: 0.8, y: 6.5, w: 0.3, h: 0.3, objectName: "al-voice-icon" });
  txt(slide, "A spoken warning plays in your ear. The caller hears nothing.", { x: 1.2, y: 6.52, w: 7, h: 0.3, fontSize: 14, color: "F6CFCB", objectName: "al-voice" });
  // Crossed-out request
  slide.addShape("roundRect", { x: 9.6, y: 0.9, w: 2.3, h: 2.3, rectRadius: 0.5, objectName: "al-glyph-bg", fill: { color: K.white, transparency: 100 }, line: { color: K.white, width: 3 } });
  slide.addImage({ data: await icon(a.glyph, K.white), x: 10.05, y: 1.35, w: 1.4, h: 1.4, objectName: "al-glyph" });
  slide.addShape("line", { x: 9.95, y: 1.25, w: 1.6, h: 1.6, flipH: true, objectName: "al-cross", line: { color: K.white, width: 5 } });
  // Buttons: ending is one tap, continuing is a hold
  txt(slide, "End call", { shape: "roundRect", rectRadius: 0.24, x: 8.95, y: 4.3, w: 3.6, h: 0.95, fill: { color: K.white }, color: K.red, fontSize: 22, bold: true, align: "center", valign: "middle", objectName: "al-end" });
  txt(slide, "Hold to keep talking", { shape: "roundRect", rectRadius: 0.24, x: 8.95, y: 5.45, w: 3.6, h: 0.8, fill: { color: K.red }, line: { color: K.white, width: 2 }, color: K.white, fontSize: 17, bold: true, align: "center", valign: "middle", objectName: "al-hold" });
  txt(slide, "End is one tap. Keeping on takes a deliberate hold.", { x: 8.95, y: 6.4, w: 3.6, h: 0.5, fontSize: 11, color: "F6CFCB", align: "center", objectName: "al-hold-note" });
}

function linkButton(slide, text, x, y, w, to, primary, dark) {
  const h = 0.62;
  const fill = primary ? (dark ? K.white : K.blue) : (dark ? K.night : K.paper);
  const fg = primary ? (dark ? K.night : K.white) : (dark ? K.white : K.blue);
  txt(slide, text, { shape: "roundRect", rectRadius: 0.18, x, y, w, h, fill: { color: fill }, line: { color: primary ? fill : (dark ? "5C7088" : K.blue), width: 1.5 }, color: fg, fontSize: 16, bold: true, align: "center", valign: "middle", objectName: "btn-" + text });
  hotspot(slide, x, y, w, h, to, text);
}

// ---------- the deck ----------
async function main() {
  const svgDot = '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"></svg>';
  HOT = "image/png;base64," + (await sharp(Buffer.from(svgDot)).png().toBuffer()).toString("base64");

  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.title = "Edgerunners: live scam protection";
  pres.author = "Team Edgerunners";
  pres.theme = { headFontFace: FONT, bodyFontFace: FONT };
  pres.defineSlideMaster({ title: "NIGHT", background: { color: K.night } });
  pres.defineSlideMaster({ title: "PAPER", background: { color: K.paper } });

  const add = (master, section) => pres.addSlide({ masterName: master, sectionTitle: section });

  // 1 Title
  pres.addSection({ title: "The problem" });
  let s = add("NIGHT", "The problem");
  await halo(s, 10.35, 3.75, 2.0, "shieldNight");
  txt(s, "LIVE SCAM PROTECTION FOR PHONE CALLS", { x: 0.8, y: 1.55, w: 7, h: 0.35, fontSize: 14, bold: true, color: K.haloBlue, charSpacing: 2, objectName: "!!kicker" });
  txt(s, "Hear the scam before you pay for it", { x: 0.8, y: 2.0, w: 6.9, h: 1.9, fontSize: 46, bold: true, color: K.white, objectName: "!!headline" });
  txt(s, "Edgerunners warns you during a call, in Punjabi, Hindi or English, on any Android phone. Only you hear it.", { x: 0.8, y: 4.2, w: 6.2, h: 1.1, fontSize: 18, color: K.muted, objectName: "!!subline" });
  linkButton(s, "Jump to the demo", 0.8, 5.95, 2.9, S.menu, false, true);
  s.addNotes("Picture someone in Ludhiana selling a scooter online. A seller calls. He's friendly. He says: I'm sending the money now, just scan this QR code and it'll come straight to you.");

  // 2 The scam
  s = add("PAPER", "The problem");
  await halo(s, 12.35, 0.95, 0.5, "watch");
  txt(s, "THE CALL", { x: 0.8, y: 0.75, w: 6, h: 0.35, fontSize: 14, bold: true, color: K.blue, charSpacing: 2, objectName: "!!kicker" });
  txt(s, "A friendly “seller” makes one request", { x: 0.8, y: 1.15, w: 10.5, h: 0.8, fontSize: 36, bold: true, color: K.ink, objectName: "!!headline" });
  s.addShape("roundRect", { x: 0.8, y: 2.45, w: 7.4, h: 3.2, rectRadius: 0.3, objectName: "quote-bg", fill: { color: K.white }, line: { color: K.line, width: 1 }, shadow: { type: "outer", color: "1F2937", opacity: 0.08, blur: 12, offset: 3, angle: 90 } });
  s.addImage({ data: await icon("MdCallReceived", K.blue), x: 1.2, y: 2.85, w: 0.45, h: 0.45, objectName: "quote-icon" });
  txt(s, "“I'm sending the money now. Just scan this QR and it'll come straight to you.”", { x: 1.2, y: 3.5, w: 6.6, h: 1.9, fontSize: 30, italic: true, color: K.ink, objectName: "!!subline" });
  txt(s, "It sounds reasonable in the moment. That's why it works.", { x: 0.8, y: 6.0, w: 7.4, h: 0.4, fontSize: 16, color: K.slate, objectName: "quote-note" });
  s.addShape("roundRect", { x: 9.0, y: 2.45, w: 3.2, h: 3.2, rectRadius: 0.4, objectName: "!!qr-bg", fill: { color: K.mist }, line: { color: K.mist, width: 0 } });
  s.addImage({ data: await icon("MdQrCode2", K.blueDark), x: 9.45, y: 2.9, w: 2.3, h: 2.3, objectName: "!!qr" });
  s.addNotes("She scans. She enters her PIN. And the money doesn't come in. It goes out.");

  // 3 The trick
  s = add("PAPER", "The problem");
  await halo(s, 12.35, 0.95, 0.5, "check");
  txt(s, "THE TRICK", { x: 0.8, y: 0.75, w: 6, h: 0.35, fontSize: 14, bold: true, color: "B26A00", charSpacing: 2, objectName: "!!kicker" });
  txt(s, "Scanning sends money out, not in", { x: 0.8, y: 1.15, w: 10.5, h: 0.8, fontSize: 36, bold: true, color: K.ink, objectName: "!!headline" });
  const steps3 = [
    ["1", "They say “scan to receive”", "A QR code or a payment request, sent while you're on the call.", K.mist, K.blueDark],
    ["2", "You scan and type your PIN", "Your UPI PIN only ever approves money leaving your account.", K.amberSoft, "6B4300"],
    ["3", "The money leaves", "The “seller” disappears with the amount on the QR.", K.pink, "8A1C14"],
  ];
  for (let i = 0; i < 3; i++) {
    const x = 0.8 + i * 4.0;
    s.addShape("roundRect", { x, y: 2.45, w: 3.6, h: 3.3, rectRadius: 0.28, objectName: "trick-card-" + i, fill: { color: K.white }, line: { color: K.line, width: 1 } });
    txt(s, steps3[i][0], { shape: "ellipse", x: x + 0.35, y: 2.8, w: 0.7, h: 0.7, fill: { color: steps3[i][3] }, color: steps3[i][4], fontSize: 22, bold: true, align: "center", valign: "middle", objectName: "trick-num-" + i });
    txt(s, steps3[i][1], { x: x + 0.35, y: 3.7, w: 2.9, h: 0.9, fontSize: 20, bold: true, color: K.ink, objectName: "trick-title-" + i });
    txt(s, steps3[i][2], { x: x + 0.35, y: 4.6, w: 2.9, h: 1.0, fontSize: 15, color: K.slate, objectName: "trick-body-" + i });
    if (i < 2) s.addImage({ data: await icon("MdArrowForward", "9AA5B1"), x: x + 3.62, y: 3.9, w: 0.36, h: 0.36, objectName: "trick-arrow-" + i });
  }
  s.addShape("roundRect", { x: 1.15, y: 2.8, w: 0.7, h: 0.7, rectRadius: 0.35, objectName: "!!qr-bg", fill: { color: K.mist, transparency: 100 }, line: { color: K.mist, width: 0, transparency: 100 } });
  s.addImage({ data: await icon("MdQrCode2", K.blueDark), x: 1.3, y: 2.95, w: 0.4, h: 0.4, transparency: 100, objectName: "!!qr" });
  txt(s, "OLX and the Delhi Police cyber cell both warn about this exact trick.", { x: 0.8, y: 6.15, w: 11, h: 0.4, fontSize: 14, color: K.slate, objectName: "!!subline" });
  s.addNotes("This is the most common payment trick on Indian marketplaces. OLX warns about it. The Delhi Police cyber cell warns about it. And it still works, because in the moment, on the phone, it sounds reasonable.");

  // 4 What exists today
  s = add("PAPER", "The problem");
  txt(s, "TODAY", { x: 0.8, y: 0.75, w: 6, h: 0.35, fontSize: 14, bold: true, color: K.blue, charSpacing: 2, objectName: "!!kicker" });
  txt(s, "Today's protection watches the wrong thing", { x: 0.8, y: 1.15, w: 11.5, h: 0.8, fontSize: 36, bold: true, color: K.ink, objectName: "!!headline" });
  const cols = [
    ["Google Scam Detection", "Warns during calls in Hindi and English, on a Pixel or a recent flagship.", "Watches: the conversation, on expensive phones"],
    ["Truecaller", "Tells you who is calling, from numbers other people reported.", "Watches: the number. A fresh SIM looks clean"],
  ];
  for (let i = 0; i < 2; i++) {
    const x = 0.8 + i * 4.0;
    s.addShape("roundRect", { x, y: 2.4, w: 3.6, h: 3.9, rectRadius: 0.28, objectName: "today-card-" + i, fill: { color: K.white }, line: { color: K.line, width: 1 } });
    txt(s, cols[i][0], { x: x + 0.35, y: 2.75, w: 2.9, h: 0.8, fontSize: 20, bold: true, color: K.ink, objectName: "today-title-" + i });
    txt(s, cols[i][1], { x: x + 0.35, y: 3.6, w: 2.9, h: 1.3, fontSize: 15, color: K.slate, objectName: "today-body-" + i });
    txt(s, cols[i][2], { x: x + 0.35, y: 5.1, w: 2.9, h: 0.9, fontSize: 13, bold: true, color: K.slate, objectName: "today-watch-" + i });
  }
  s.addShape("roundRect", { x: 8.8, y: 2.4, w: 3.73, h: 3.9, rectRadius: 0.28, objectName: "today-card-us", fill: { color: K.night }, line: { color: K.night, width: 0 } });
  await halo(s, 9.65, 3.22, 0.46, "shieldNight");
  txt(s, "Edgerunners", { x: 10.45, y: 3.02, w: 2.2, h: 0.4, fontSize: 20, bold: true, color: K.white, objectName: "today-title-us" });
  txt(s, "Listens for what the caller asks you to do: scan a QR, type a PIN, share an OTP.", { x: 9.15, y: 4.05, w: 3.1, h: 1.1, fontSize: 15, color: "DCE6EF", objectName: "today-body-us" });
  txt(s, "Punjabi, Hindi, English or mixed. Any Android phone", { x: 9.15, y: 5.25, w: 3.1, h: 0.8, fontSize: 13, bold: true, color: K.haloBlue, objectName: "today-watch-us" });
  s.addNotes("There is protection today. Google warns you during scam calls, in Hindi and English, on a Pixel or a recent flagship. Truecaller tells you who is calling, from numbers other people reported. A scammer on a fresh SIM looks clean.");

  // 5 The question
  pres.addSection({ title: "Our answer" });
  s = add("NIGHT", "Our answer");
  await halo(s, W / 2, H / 2, 2.6, "faint");
  txt(s, "Not who is calling.", { x: 0.8, y: 2.35, w: W - 1.6, h: 0.9, fontSize: 40, bold: true, color: K.muted, align: "center", objectName: "!!kicker" });
  txt(s, "What are they asking you to do?", { x: 0.8, y: 3.3, w: W - 1.6, h: 1.2, fontSize: 54, bold: true, color: K.white, align: "center", objectName: "!!headline" });
  s.addNotes("We asked a different question. Not who is calling. What are they asking you to do? Edgerunners listens for the request itself: scan a QR to receive money, type your UPI PIN, share an OTP.");

  // 6 Menu
  s = add("NIGHT", "Our answer");
  await screenHome(s);
  txt(s, "TRY IT", { x: 0.8, y: 0.8, w: 6, h: 0.35, fontSize: 14, bold: true, color: K.haloBlue, charSpacing: 2, objectName: "!!kicker" });
  txt(s, "Pick a call", { x: 0.8, y: 1.2, w: 7, h: 0.8, fontSize: 40, bold: true, color: K.white, objectName: "!!headline" });
  const menu = [
    ["MdQrCode2", "A “seller” asks you to scan a QR", "Marketplace payment scam", S.qrRing, K.pink, "8A1C14"],
    ["MdPassword", "A caller asks for your OTP", "Bank or delivery impersonation", S.otpCheck, K.amberSoft, "6B4300"],
    ["MdCall", "An ordinary call", "No payment requests", S.calmListen, K.mist, K.blueDark],
  ];
  for (let i = 0; i < 3; i++) {
    const y = 2.3 + i * 1.22;
    s.addShape("roundRect", { x: 0.8, y, w: 6.9, h: 1.02, rectRadius: 0.22, objectName: "menu-card-" + i, fill: { color: "16283A" }, line: { color: "2F4A63", width: 1.25 } });
    s.addShape("roundRect", { x: 1.05, y: y + 0.19, w: 0.64, h: 0.64, rectRadius: 0.16, objectName: "menu-badge-" + i, fill: { color: menu[i][4] }, line: { color: menu[i][4], width: 0 } });
    s.addImage({ data: await icon(menu[i][0], menu[i][5]), x: 1.19, y: y + 0.33, w: 0.36, h: 0.36, objectName: "menu-icon-" + i });
    txt(s, menu[i][1], { x: 1.95, y: y + 0.17, w: 5, h: 0.4, fontSize: 18, bold: true, color: K.white, objectName: "menu-title-" + i });
    txt(s, menu[i][2], { x: 1.95, y: y + 0.57, w: 5, h: 0.3, fontSize: 13, color: K.muted, objectName: "menu-sub-" + i });
    s.addImage({ data: await icon("MdArrowForward", K.haloBlue), x: 7.1, y: y + 0.36, w: 0.3, h: 0.3, objectName: "menu-go-" + i });
    hotspot(s, 0.8, y, 6.9, 1.02, menu[i][3], menu[i][1]);
  }
  txt(s, "Skip to how it works", { x: 0.8, y: 6.15, w: 3.2, h: 0.4, fontSize: 15, bold: true, color: K.haloBlue, objectName: "menu-skip" });
  hotspot(s, 0.8, 6.05, 3.2, 0.6, S.how, "Skip to how it works");
  s.addNotes("Click a call to play it. Each one ends with buttons to come back here or move on.");

  // 7 Incoming
  pres.addSection({ title: "Demo calls" });
  s = add("NIGHT", "Demo calls");
  await screenIncoming(s);
  step(s, "1 · THE PHONE RINGS", "The caller uses any phone", "No app on their side, just the default dialer. Our user answers in Edgerunners.", "Click Answer on the phone");
  hotspot(s, P.x + P.w - 1.4, 5.55, 0.9, 1.0, S.qrListen, "Answer");
  s.addNotes("[CALLER] is calling from a normal phone. No app on that side. Our user answers in Edgerunners.");

  // 8 Listening
  s = add("NIGHT", "Demo calls");
  await screenCall(s, "listen", "0:04");
  step(s, "2 · LISTENING", "The halo breathes while it listens", "You can forget it's there. Nothing happens unless the caller asks for a payment, PIN or OTP.");
  s.addNotes("See this ring? That's scam check. It breathes slowly while it listens. You can forget it's there.");

  // 9 Checking
  s = add("NIGHT", "Demo calls");
  await screenCall(s, "check", "0:21", "QR code to “receive” money");
  step(s, "3 · THEY ASK", "A chime, a buzz, an amber halo", "Our target: within 2 seconds of the request, from an instant phrase check. The AI check confirms the level next.");
  s.addNotes("That chime and the buzz came [MEASURED: X] seconds after he asked. The ring turned amber: we're checking.");

  // 10 QR alert
  s = add("NIGHT", "Demo calls");
  await alertSlide(s, {
    title: "They asked you to scan a QR code to receive money.",
    truth: "Receiving money never needs a QR scan or your UPI PIN. Scanning sends money out.",
    next: "End the call. Check for the payment in your own bank app.",
    glyph: "MdQrCode2",
  });
  hotspot(s, 8.95, 4.3, 3.6, 0.95, S.qrStory, "End call");
  s.addNotes("High risk. It tells her exactly what happened, then the truth, then what to do. End call is one tap. Keeping on talking means pressing and holding. And the caller heard nothing. Click End call.");

  // 11 QR story
  s = add("PAPER", "Demo calls");
  await halo(s, 12.35, 0.95, 0.5, "watch");
  txt(s, "CALL STORY", { x: 0.8, y: 0.75, w: 6, h: 0.35, fontSize: 14, bold: true, color: K.blue, charSpacing: 2, objectName: "!!kicker" });
  txt(s, "We stepped in the moment they asked", { x: 0.8, y: 1.15, w: 10.5, h: 0.8, fontSize: 36, bold: true, color: K.ink, objectName: "!!headline" });
  s.addShape("roundRect", { x: 0.8, y: 2.35, w: 7.4, h: 3.3, rectRadius: 0.28, objectName: "story-card", fill: { color: K.white }, line: { color: K.line, width: 1 } });
  s.addShape("roundRect", { x: 1.2, y: 2.85, w: 6.6, h: 0.14, rectRadius: 0.07, objectName: "story-bar", fill: { color: K.mist }, line: { color: K.mist, width: 0 } });
  const marks = [[0.62, "E8A317", "0:21", "Asked you to scan a QR code"], [0.72, K.redBright, "0:24", "High risk confirmed"], [0.82, K.blue, "0:27", "You ended the call"]];
  marks.forEach(([p, c, t, label], i) => {
    s.addShape("ellipse", { x: 1.2 + 6.6 * p - 0.14, y: 2.78, w: 0.28, h: 0.28, objectName: "story-dot-" + i, fill: { color: c }, line: { color: K.white, width: 2 } });
    s.addShape("ellipse", { x: 1.2, y: 3.62 + i * 0.6, w: 0.2, h: 0.2, objectName: "story-key-" + i, fill: { color: c }, line: { color: c, width: 0 } });
    txt(s, t, { x: 1.55, y: 3.53 + i * 0.6, w: 0.8, h: 0.4, fontSize: 15, color: K.slate, objectName: "story-time-" + i });
    txt(s, label, { x: 2.4, y: 3.53 + i * 0.6, w: 5.3, h: 0.4, fontSize: 17, bold: true, color: K.ink, objectName: "story-label-" + i });
  });
  s.addShape("roundRect", { x: 8.75, y: 2.35, w: 3.8, h: 3.3, rectRadius: 0.28, objectName: "story-lock-bg", fill: { color: K.mist }, line: { color: K.mist, width: 0 } });
  s.addImage({ data: await icon("MdLockOutline", K.blueDark), x: 9.15, y: 2.75, w: 0.5, h: 0.5, objectName: "story-lock-icon" });
  txt(s, "Nothing recorded", { x: 9.15, y: 3.4, w: 3.1, h: 0.45, fontSize: 20, bold: true, color: K.blueDark, objectName: "story-lock-title" });
  txt(s, "No audio. No transcript. Only these moments, kept on your phone.", { x: 9.15, y: 3.9, w: 3.1, h: 1.3, fontSize: 15, color: K.blueDark, objectName: "!!subline" });
  linkButton(s, "Try another call", 0.8, 6.1, 3.0, S.menu, false, false);
  linkButton(s, "Continue", 4.0, 6.1, 2.4, S.how, true, false);
  s.addNotes("After the call, a short story: when we stepped in, what she chose. Nothing from the call was recorded or kept.");

  // 12 OTP checking
  s = add("NIGHT", "Demo calls");
  await screenCall(s, "check", "0:38", "a one-time password (OTP)");
  step(s, "THE OTP CALL", "“Just read me the code we sent”", "Bank and delivery impersonators ask for the OTP. The halo turns amber the moment they do.");
  s.addNotes("Same flow, different scam: a caller pretending to be the bank asks for the OTP.");

  // 13 OTP alert
  s = add("NIGHT", "Demo calls");
  await alertSlide(s, {
    title: "They asked you to share an OTP.",
    truth: "An OTP lets someone take money or your account. Real banks never ask for it on a call.",
    next: "End the call. If it mattered, call the number on your card.",
    glyph: "MdPassword",
  });
  hotspot(s, 8.95, 4.3, 3.6, 0.95, S.menu, "End call and pick another");
  s.addNotes("High risk, every time: an OTP request on a call is never routine. Click End call to go back to the calls.");

  // 14 Ordinary call
  s = add("NIGHT", "Demo calls");
  await screenCall(s, "listen", "1:12");
  step(s, "AN ORDINARY CALL", "No request, no interruption", "No chime, no buzz, no alert. Scam check stays quiet when there's nothing to warn about.");
  s.addNotes("Most calls are like this. The app stays out of the way.");

  // 15 Ordinary story
  s = add("PAPER", "Demo calls");
  await halo(s, 12.35, 0.95, 0.5, "watch");
  txt(s, "CALL STORY", { x: 0.8, y: 0.75, w: 6, h: 0.35, fontSize: 14, bold: true, color: K.blue, charSpacing: 2, objectName: "!!kicker" });
  txt(s, "We didn't hear any request for a QR scan, UPI PIN or OTP", { x: 0.8, y: 1.15, w: 10.8, h: 1.4, fontSize: 36, bold: true, color: K.ink, objectName: "!!headline" });
  s.addShape("roundRect", { x: 0.8, y: 2.95, w: 11.75, h: 1.75, rectRadius: 0.28, objectName: "story-card", fill: { color: K.white }, line: { color: K.line, width: 1 } });
  s.addImage({ data: await icon("MdBlock", K.blue), x: 1.25, y: 3.4, w: 0.6, h: 0.6, objectName: "calm-icon" });
  txt(s, "We never say a call is safe", { x: 2.15, y: 3.35, w: 9.5, h: 0.5, fontSize: 22, bold: true, color: K.ink, objectName: "calm-title" });
  txt(s, "No check can promise that. We only say what we heard. That's why the halo is never green.", { x: 2.15, y: 3.9, w: 9.8, h: 0.9, fontSize: 17, color: K.slate, objectName: "!!subline" });
  linkButton(s, "Try another call", 0.8, 6.1, 3.0, S.menu, false, false);
  linkButton(s, "Continue", 4.0, 6.1, 2.4, S.how, true, false);
  s.addNotes("The app never says a call is safe, because no check can promise that.");

  // 16 How it works
  pres.addSection({ title: "How it works" });
  s = add("PAPER", "How it works");
  txt(s, "HOW IT WORKS", { x: 0.8, y: 0.75, w: 6, h: 0.35, fontSize: 14, bold: true, color: K.blue, charSpacing: 2, objectName: "!!kicker" });
  txt(s, "From their words to your warning", { x: 0.8, y: 1.15, w: 10.5, h: 0.8, fontSize: 36, bold: true, color: K.ink, objectName: "!!headline" });
  const nodes = [
    ["MdSmartphone", "Any phone", "The caller dials our number from their normal dialer."],
    ["MdCallMade", "Twilio", "Connects the call and streams the caller's audio."],
    ["MdTranslate", "Sarvam", "Turns speech into text live: Punjabi, Hindi, English, mixed."],
    ["MdGraphicEq", "Two checks", "An instant phrase check warns first. An AI check confirms the level."],
  ];
  const gap = 0.38, nw = (W - 1.6 - 4 * gap) / 5;
  for (let i = 0; i < 4; i++) {
    const x = 0.8 + i * (nw + gap);
    s.addShape("roundRect", { x, y: 2.4, w: nw, h: 3.2, rectRadius: 0.24, objectName: "node-" + i, fill: { color: K.white }, line: { color: K.line, width: 1 } });
    s.addShape("ellipse", { x: x + 0.3, y: 2.7, w: 0.62, h: 0.62, objectName: "node-badge-" + i, fill: { color: K.mist }, line: { color: K.mist, width: 0 } });
    s.addImage({ data: await icon(nodes[i][0], K.blueDark), x: x + 0.44, y: 2.84, w: 0.34, h: 0.34, objectName: "node-icon-" + i });
    txt(s, nodes[i][1], { x: x + 0.3, y: 3.5, w: nw - 0.5, h: 0.4, fontSize: 18, bold: true, color: K.ink, objectName: "node-title-" + i });
    txt(s, nodes[i][2], { x: x + 0.3, y: 3.95, w: nw - 0.5, h: 1.5, fontSize: 14, color: K.slate, objectName: "node-body-" + i });
    s.addImage({ data: await icon("MdArrowForward", "9AA5B1"), x: x + nw + 0.04, y: 3.83, w: 0.3, h: 0.3, objectName: "node-arrow-" + i });
  }
  const ux = 0.8 + 4 * (nw + gap);
  s.addShape("roundRect", { x: ux, y: 2.4, w: nw, h: 3.2, rectRadius: 0.24, objectName: "node-us", fill: { color: K.night }, line: { color: K.night, width: 0 } });
  await halo(s, ux + 0.61, 3.01, 0.44, "shieldNight");
  txt(s, "Your app", { x: ux + 0.3, y: 3.5, w: nw - 0.4, h: 0.4, fontSize: 18, bold: true, color: K.white, objectName: "node-title-us" });
  txt(s, "Only you get the chime, buzz and spoken warning.", { x: ux + 0.3, y: 3.95, w: nw - 0.5, h: 1.5, fontSize: 14, color: "DCE6EF", objectName: "node-body-us" });
  txt(s, "Stored: no audio and no transcript.   Said: never “safe”.", { x: 0.8, y: 6.0, w: 11.5, h: 0.4, fontSize: 16, bold: true, color: K.slate, objectName: "!!subline" });
  s.addNotes("The caller dials our number through Twilio. The caller's audio streams to Sarvam's speech recognition, which handles Punjabi, Hindi, English and mixed speech. Two checks run: an instant phrase check for the first warning, and an AI check that confirms the level. The warning goes only to the protected user's app.");

  // 17 Rules
  s = add("PAPER", "How it works");
  await halo(s, 12.35, 0.95, 0.5, "watch");
  txt(s, "DESIGN RULES", { x: 0.8, y: 0.75, w: 6, h: 0.35, fontSize: 14, bold: true, color: K.blue, charSpacing: 2, objectName: "!!kicker" });
  txt(s, "Four rules we never break", { x: 0.8, y: 1.15, w: 10.5, h: 0.8, fontSize: 36, bold: true, color: K.ink, objectName: "!!headline" });
  const rules = [
    ["MdBlock", "Never says “safe”", "No check can promise a call is safe, so the app never does. The halo is never green."],
    ["MdTouchApp", "One tap to end, a hold to go on", "Ending the call is the biggest button. Keeping on talking takes a deliberate press and hold."],
    ["MdLockOutline", "Nothing recorded", "No audio and no transcript are stored. The call story keeps only request types and times."],
    ["MdSmartphone", "Any Android phone", "The checking runs on our server, so a budget phone gets the same protection."],
  ];
  for (let i = 0; i < 4; i++) {
    const x = 0.8 + (i % 2) * 6.0, y = 2.3 + Math.floor(i / 2) * 2.15;
    s.addShape("roundRect", { x, y, w: 5.75, h: 1.9, rectRadius: 0.24, objectName: "rule-" + i, fill: { color: K.white }, line: { color: K.line, width: 1 } });
    s.addShape("ellipse", { x: x + 0.35, y: y + 0.35, w: 0.7, h: 0.7, objectName: "rule-badge-" + i, fill: { color: K.mist }, line: { color: K.mist, width: 0 } });
    s.addImage({ data: await icon(rules[i][0], K.blueDark), x: x + 0.51, y: y + 0.51, w: 0.38, h: 0.38, objectName: "rule-icon-" + i });
    txt(s, rules[i][1], { x: x + 1.3, y: y + 0.3, w: 4.2, h: 0.45, fontSize: 20, bold: true, color: K.ink, objectName: "rule-title-" + i });
    txt(s, rules[i][2], { x: x + 1.3, y: y + 0.8, w: 4.2, h: 0.95, fontSize: 15, color: K.slate, objectName: "rule-body-" + i });
  }
  s.addNotes("Two rules we never break: the app never says a call is safe, and we store no audio and no transcript.");

  // 18 Next
  s = add("PAPER", "How it works");
  await halo(s, 12.35, 0.95, 0.5, "watch");
  txt(s, "NEXT", { x: 0.8, y: 0.75, w: 6, h: 0.35, fontSize: 14, bold: true, color: K.blue, charSpacing: 2, objectName: "!!kicker" });
  txt(s, "Where it goes after this weekend", { x: 0.8, y: 1.15, w: 10.5, h: 0.8, fontSize: 36, bold: true, color: K.ink, objectName: "!!headline" });
  const nexts = [
    ["MdPhoneForwarded", "Your own number", "Forward unknown calls from your number to the service."],
    ["MdChatBubbleOutline", "Before the call", "Flag a QR image or payment link sent in chat."],
    ["MdGroups", "Account reputation", "Platforms see repeat offenders by account, not number."],
    ["MdMemory", "On-phone model", "Keep audio on the device once budget phones can run it."],
  ];
  s.addShape("line", { x: 1.15, y: 2.85, w: 9.0, h: 0, objectName: "next-line", line: { color: K.grey, width: 2 } });
  for (let i = 0; i < 4; i++) {
    const x = 0.8 + i * 3.0;
    s.addShape("ellipse", { x: x, y: 2.5, w: 0.7, h: 0.7, objectName: "next-dot-" + i, fill: { color: i === 0 ? K.blue : K.white }, line: { color: K.blue, width: 2 } });
    s.addImage({ data: await icon(nexts[i][0], i === 0 ? K.white : K.blue), x: x + 0.17, y: 2.67, w: 0.36, h: 0.36, objectName: "next-icon-" + i });
    txt(s, nexts[i][1], { x, y: 3.5, w: 2.7, h: 0.45, fontSize: 20, bold: true, color: K.ink, objectName: "next-title-" + i });
    txt(s, nexts[i][2], { x, y: 4.0, w: 2.6, h: 1.2, fontSize: 15, color: K.slate, objectName: "next-body-" + i });
  }
  txt(s, "Business model: platforms pay per protected call minute.", { x: 0.8, y: 6.0, w: 11.5, h: 0.4, fontSize: 16, bold: true, color: K.slate, objectName: "!!subline" });
  s.addNotes("Roadmap only; none of this is built yet. Say so if asked.");

  // 19 Close
  pres.addSection({ title: "Close" });
  s = add("NIGHT", "Close");
  await halo(s, W / 2, 2.05, 1.1, "shieldNight");
  txt(s, "Google protects Hindi and English calls on a Pixel. Truecaller tells you who's calling.", { x: 1.2, y: 4.05, w: W - 2.4, h: 0.9, fontSize: 20, color: K.muted, align: "center", objectName: "!!kicker" });
  txt(s, "Edgerunners listens for what they're asking you to do, and warns only you, in time to hang up.", { x: 1.2, y: 4.85, w: W - 2.4, h: 1.4, fontSize: 32, bold: true, color: K.white, align: "center", objectName: "!!headline" });
  txt(s, "Thank you", { x: 1.2, y: 6.45, w: W - 2.4, h: 0.4, fontSize: 16, bold: true, color: K.haloBlue, align: "center", objectName: "!!subline" });
  s.addNotes("We're [TEAM NAMES]. Thank you.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  await addMorph(OUT, { [S.qrListen]: 3500, [S.qrCheck]: 3200, [S.otpCheck]: 3200, [S.calmListen]: 4000 });
  console.log("wrote", OUT);
}

// Morph on every slide; a few demo slides advance on their own like a real call.
async function addMorph(file, autoAdvance) {
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const names = Object.keys(zip.files).filter((n) => /^ppt\/slides\/slide\d+\.xml$/.test(n));
  for (const n of names) {
    const num = Number(n.match(/slide(\d+)\.xml/)[1]);
    let xml = await zip.file(n).async("string");
    const adv = autoAdvance[num] ? ` advTm="${autoAdvance[num]}"` : "";
    const tr =
      '<mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">' +
      '<mc:Choice xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main" Requires="p159">' +
      `<p:transition spd="slow" p14:dur="1100" xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main"${adv}><p159:morph option="byObject"/></p:transition>` +
      "</mc:Choice>" +
      `<mc:Fallback><p:transition spd="slow"${adv}><p:fade/></p:transition></mc:Fallback>` +
      "</mc:AlternateContent>";
    if (xml.includes("<p:transition")) throw new Error("transition already present in " + n);
    xml = xml.replace("</p:clrMapOvr>", "</p:clrMapOvr>" + tr);
    if (!xml.includes("p159:morph")) throw new Error("no clrMapOvr in " + n);
    zip.file(n, xml);
  }
  fs.writeFileSync(file, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}

main().catch((e) => { console.error(e); process.exit(1); });
