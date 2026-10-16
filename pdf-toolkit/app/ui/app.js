"use strict";

// --------------------------------------------------------------------------- icons

const ICONS = {
  compress: '<svg viewBox="0 0 24 24"><path d="M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7"/></svg>',
  merge: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="8" height="10" rx="1.5"/><rect x="13" y="3" width="8" height="10" rx="1.5"/><path d="M7 13v3a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2v-3M12 18v3"/></svg>',
  pdfToImg: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2.5"/><circle cx="9" cy="9" r="2"/><path d="M21 15l-4.5-4.5L6 21"/></svg>',
  imgCompress: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2.5"/><path d="M7.5 7.5l3.5 3.5M11 7.5V11H7.5M16.5 16.5L13 13M13 16.5V13h3.5"/></svg>',
  imgToPdf: '<svg viewBox="0 0 24 24"><path d="M6 2h8l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/><path d="M14 2v5h5"/><circle cx="9.5" cy="12" r="1.5"/><path d="M18 18l-3.5-3.5L8 21"/></svg>',
  pdf: '<svg viewBox="0 0 24 24"><path d="M6 2h8l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/><path d="M14 2v5h5"/></svg>',
  image: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2.5"/><circle cx="9" cy="9" r="2"/><path d="M21 15l-4.5-4.5L6 21"/></svg>',
  plus: '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>',
  close: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  check: '<svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
  alert: '<svg viewBox="0 0 24 24"><path d="M12 8v5M12 16.5v.01"/><circle cx="12" cy="12" r="9"/></svg>',
};

// --------------------------------------------------------------------------- tools

const TOOLS = {
  "compress-pdf": {
    section: "PDF",
    name: "Compress PDF",
    icon: ICONS.compress,
    kind: "pdf",
    desc: "Make PDFs smaller by shrinking the images inside them.",
    drop: "Drop PDF files here",
    run: "Compress PDF",
    defaults: { level: "recommended", grayscale: false },
    done: "Your PDFs are compressed",
    options: (o) => [
      levels("Compression level", "level", [
        ["light", "Light", "Best quality, smaller savings (150 dpi)"],
        ["recommended", "Recommended", "Good quality, good savings (120 dpi)"],
        ["extreme", "Extreme", "Smallest file, lower quality (72 dpi)"],
      ]),
      check("Convert to grayscale", "grayscale", "Removes color for extra savings."),
    ],
  },
  "merge-pdf": {
    section: "PDF",
    name: "Merge PDF",
    icon: ICONS.merge,
    kind: "pdf",
    ordered: true,
    min: 2,
    desc: "Combine several PDFs into one, in the order you choose.",
    drop: "Drop PDF files here",
    run: "Merge PDF",
    defaults: { fileName: "merged" },
    done: "Your PDFs are merged",
    options: () => [text("Output file name", "fileName", ".pdf")],
  },
  "pdf-to-images": {
    section: "PDF",
    name: "PDF to Images",
    icon: ICONS.pdfToImg,
    kind: "pdf",
    desc: "Turn every page into a PNG or JPG image.",
    drop: "Drop PDF files here",
    run: "Convert to images",
    defaults: { format: "png", dpi: 150, pages: "" },
    done: "Your pages are images now",
    options: () => [
      seg("Image format", "format", [["png", "PNG"], ["jpg", "JPG"]],
        "PNG is sharper; JPG is much smaller."),
      seg("Resolution", "dpi", [[72, "72 dpi"], [150, "150 dpi"], [300, "300 dpi"]],
        "72 for screens, 150 for most uses, 300 for printing."),
      text("Pages", "pages", null, "All pages (e.g. 1-3, 5)"),
    ],
  },
  "compress-images": {
    section: "Images",
    name: "Compress Images",
    icon: ICONS.imgCompress,
    kind: "image",
    desc: "Shrink JPG, PNG and WebP images, optionally resizing them.",
    drop: "Drop images here",
    run: "Compress images",
    defaults: { quality: 75, maxDim: 0, format: "keep" },
    done: "Your images are compressed",
    options: (o) => [
      range("Quality", "quality", 10, 95, "Smaller", "Better"),
      select("Maximum size", "maxDim", [
        [0, "Keep original size"], [3840, "3840 px (4K)"], [2560, "2560 px"],
        [1920, "1920 px (Full HD)"], [1280, "1280 px"], [800, "800 px"],
      ], "Longest side. Images are never enlarged."),
      select("Save as", "format", [
        ["keep", "Same as original"], ["jpg", "JPG"], ["webp", "WebP"], ["png", "PNG"],
      ]),
    ],
  },
  "images-to-pdf": {
    section: "Images",
    name: "Images to PDF",
    icon: ICONS.imgToPdf,
    kind: "image",
    ordered: true,
    min: 1,
    desc: "Put images into a single PDF, one image per page.",
    drop: "Drop images here",
    run: "Create PDF",
    defaults: { pageSize: "fit", orientation: "auto", margin: 0, fileName: "images" },
    done: "Your PDF is ready",
    options: (o) => [
      seg("Page size", "pageSize", [["fit", "Fit image"], ["a4", "A4"], ["letter", "Letter"]]),
      seg("Orientation", "orientation", [["auto", "Auto"], ["portrait", "Portrait"], ["landscape", "Landscape"]],
        null, o.pageSize === "fit"),
      seg("Margin", "margin", [[0, "None"], [18, "Small"], [36, "Large"]]),
      text("Output file name", "fileName", ".pdf"),
    ],
  },
};

// --------------------------------------------------------------------------- state

const state = {
  tool: "compress-pdf",
  files: {},      // tool -> [{path, name, size, kind}]
  opts: {},       // tool -> options object
  outDir: {},     // tool -> folder or null
  view: {},       // tool -> "files" | "results"
  results: {},    // tool -> response from api.run
  running: null,  // tool currently running
};
for (const [id, t] of Object.entries(TOOLS)) {
  state.files[id] = [];
  state.opts[id] = { ...t.defaults };
  state.outDir[id] = null;
  state.view[id] = "files";
}
const thumbs = new Map(); // path -> {thumb, pages} | "loading"

const $ = (id) => document.getElementById(id);
const api = () => window.pywebview.api;
const tool = () => TOOLS[state.tool];

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

function formatBytes(n) {
  if (n == null) return "";
  if (n < 1024) return `${n} B`;
  const units = ["KB", "MB", "GB"];
  let i = -1;
  do { n /= 1024; i++; } while (n >= 1024 && i < units.length - 1);
  return `${n.toFixed(n < 10 ? 1 : 0)} ${units[i]}`;
}

function basename(p) {
  return p.split(/[\\/]/).pop();
}

function toast(message, isError = false) {
  const el = h("div", { class: "toast" + (isError ? " err" : "") }, message);
  $("toasts").append(el);
  setTimeout(() => el.remove(), isError ? 6000 : 3500);
}

// --------------------------------------------------------------------------- option widgets

function setOpt(key, value) {
  state.opts[state.tool][key] = value;
  renderOptions();
}

function group(label, control, help, valueText) {
  return h("div", { class: "opt-group" },
    h("div", { class: "opt-label" }, label, valueText != null ? h("span", { class: "value" }, valueText) : null),
    control,
    help ? h("div", { class: "opt-help" }, help) : null);
}

function levels(label, key, choices) {
  const cur = state.opts[state.tool][key];
  return group(label, h("div", { class: "levels" }, choices.map(([v, name, desc]) =>
    h("button", { type: "button", class: "level" + (cur === v ? " active" : ""), onclick: () => setOpt(key, v) },
      h("span", { class: "dot" }),
      h("span", {}, h("div", { class: "level-name" }, name), h("div", { class: "level-desc" }, desc))))));
}

function seg(label, key, choices, help, disabled) {
  const cur = state.opts[state.tool][key];
  return group(label, h("div", { class: "seg" + (disabled ? " disabled" : "") }, choices.map(([v, text]) =>
    h("button", { type: "button", class: cur === v ? "active" : "", onclick: () => setOpt(key, v) }, text))), help);
}

function check(label, key, help) {
  const input = h("input", { type: "checkbox", checked: !!state.opts[state.tool][key] });
  input.addEventListener("change", () => setOpt(key, input.checked));
  return h("div", { class: "opt-group" },
    h("label", { class: "check" }, input, h("span", {}, label)),
    help ? h("div", { class: "opt-help" }, help) : null);
}

function text(label, key, suffix, placeholder) {
  const input = h("input", { class: "field", type: "text", value: state.opts[state.tool][key] ?? "",
    placeholder, spellcheck: "false" });
  input.addEventListener("input", () => { state.opts[state.tool][key] = input.value; });
  const control = suffix ? h("div", { class: "field-suffix" }, input, suffix) : input;
  return group(label, control);
}

function range(label, key, min, max, lowText, highText) {
  const value = state.opts[state.tool][key];
  const input = h("input", { type: "range", min, max, value });
  const node = group(label, h("div", {}, input,
    h("div", { class: "range-ends" }, h("span", {}, lowText), h("span", {}, highText))), null, value);
  input.addEventListener("input", () => {
    state.opts[state.tool][key] = Number(input.value);
    node.querySelector(".value").textContent = input.value;
  });
  return node;
}

function select(label, key, choices, help) {
  const cur = state.opts[state.tool][key];
  const el = h("select", { class: "field" }, choices.map(([v, text]) =>
    h("option", { value: String(v), selected: String(v) === String(cur) }, text)));
  el.addEventListener("change", () => {
    const picked = choices.find(([v]) => String(v) === el.value)[0];
    setOpt(key, picked);
  });
  return group(label, el, help);
}

// --------------------------------------------------------------------------- rendering

function renderNav() {
  const nav = $("nav");
  nav.replaceChildren();
  let section = null;
  for (const [id, t] of Object.entries(TOOLS)) {
    if (t.section !== section) {
      section = t.section;
      nav.append(h("div", { class: "nav-section" }, section));
    }
    const count = state.files[id].length;
    nav.append(h("button", {
      type: "button",
      class: "nav-item" + (id === state.tool ? " active" : ""),
      "aria-current": id === state.tool ? "page" : null,
      onclick: () => switchTool(id),
      html: t.icon,
    }, h("span", {}, t.name), count && id !== state.tool ? h("span", { class: "badge" }, count) : null));
  }
}

function render() {
  const t = tool();
  renderNav();
  $("tool-title").textContent = t.name;
  $("tool-desc").textContent = t.desc;

  const files = state.files[state.tool];
  const showResults = state.view[state.tool] === "results" && state.results[state.tool];
  $("empty").hidden = showResults || files.length > 0;
  $("workspace").hidden = showResults || files.length === 0;
  $("results").hidden = !showResults;

  if (!$("empty").hidden) {
    $("dz-icon").innerHTML = t.icon;
    $("dz-title").textContent = t.drop;
    $("dz-hint").textContent = t.kind === "pdf"
      ? "PDF files · you can also drop folders"
      : "JPG, PNG, WebP, BMP or TIFF · you can also drop folders";
  }
  if (!$("workspace").hidden) {
    renderFiles();
    renderOptions();
    renderRunState();
  }
  if (showResults) renderResults();
}

function renderFiles() {
  const t = tool();
  const files = state.files[state.tool];
  const grid = $("file-grid");
  grid.replaceChildren();

  const noun = t.kind === "pdf" ? "PDF" : "image";
  $("files-count").textContent = `${files.length} ${noun}${files.length === 1 ? "" : "s"} · ${formatBytes(files.reduce((s, f) => s + f.size, 0))}`;
  $("sort-az").hidden = !t.ordered;
  $("reverse").hidden = !t.ordered;
  $("order-hint").hidden = !t.ordered || files.length < 2;

  files.forEach((f, i) => grid.append(fileCard(f, i, t.ordered)));
  grid.append(h("div", { class: "card add", role: "button", tabindex: "0", onclick: browse, html: ICONS.plus },
    h("span", {}, "Add more")));
}

function fileCard(f, index, ordered) {
  const info = thumbs.get(f.path);
  const thumb = h("div", { class: "thumb" });
  if (info && info !== "loading" && info.thumb) {
    thumb.append(h("img", { src: info.thumb, alt: "", draggable: "false" }));
  } else {
    thumb.append(h("div", { class: "ph" + (info === "loading" || !info ? " loading" : ""),
      html: f.kind === "pdf" ? ICONS.pdf : ICONS.image }));
  }
  const pages = info && info !== "loading" && info.pages
    ? ` · ${info.pages} page${info.pages === 1 ? "" : "s"}` : "";

  const card = h("div", { class: "card" + (ordered ? " draggable" : ""), title: f.path },
    ordered ? h("div", { class: "card-index" }, index + 1) : null,
    h("button", { type: "button", class: "card-remove", title: "Remove", "aria-label": `Remove ${f.name}`,
      html: ICONS.close, onclick: (e) => { e.stopPropagation(); removeFile(index); } }),
    thumb,
    h("div", { class: "card-name" }, f.name),
    h("div", { class: "card-meta" }, formatBytes(f.size) + pages));

  if (ordered && !state.running) enableReorder(card, index);
  return card;
}

let dragFrom = null;

function enableReorder(card, index) {
  card.draggable = true;
  card.addEventListener("dragstart", (e) => {
    dragFrom = index;
    card.classList.add("dragging");
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", String(index));
  });
  card.addEventListener("dragend", () => {
    dragFrom = null;
    document.querySelectorAll(".card").forEach((c) => c.classList.remove("dragging", "drop-before", "drop-after"));
  });
  card.addEventListener("dragover", (e) => {
    if (dragFrom == null) return;
    e.preventDefault();
    const after = e.offsetX > card.clientWidth / 2;
    card.classList.toggle("drop-after", after);
    card.classList.toggle("drop-before", !after);
  });
  card.addEventListener("dragleave", () => card.classList.remove("drop-before", "drop-after"));
  card.addEventListener("drop", (e) => {
    if (dragFrom == null) return;
    e.preventDefault();
    e.stopPropagation();
    const after = e.offsetX > card.clientWidth / 2;
    const files = state.files[state.tool];
    const [moved] = files.splice(dragFrom, 1);
    let to = index + (after ? 1 : 0);
    if (dragFrom < to) to--;
    files.splice(to, 0, moved);
    dragFrom = null;
    renderFiles();
  });
}

function renderOptions() {
  const box = $("options");
  box.replaceChildren(...tool().options(state.opts[state.tool]));
  const dir = state.outDir[state.tool];
  $("outdir-path").textContent = dir || "Same folder as the original";
  $("outdir-path").title = dir || "";
  $("outdir-reset").hidden = !dir;
}

function renderRunState() {
  const t = tool();
  const files = state.files[state.tool];
  const running = state.running === state.tool;
  const run = $("run");
  run.textContent = running ? "Working…" : t.run;
  const min = t.min || 1;
  run.disabled = !!state.running || files.length < min;
  run.title = files.length < min ? `Add at least ${min} files` : "";
  $("progress").hidden = !running;
  for (const id of ["sort-az", "reverse", "clear", "outdir-change", "outdir-reset"]) $(id).disabled = !!state.running;
  $("options").style.pointerEvents = running ? "none" : "";
  $("options").style.opacity = running ? ".6" : "";
}

function renderResults() {
  const t = tool();
  const res = state.results[state.tool];
  const items = res.results || [];
  const ok = items.filter((r) => r.ok);
  const failed = items.filter((r) => !r.ok);

  const icon = document.querySelector(".results-icon");
  icon.classList.toggle("warn", ok.length === 0);
  icon.innerHTML = ok.length === 0 ? ICONS.alert : ICONS.check;

  $("results-title").textContent = ok.length === 0 ? "Nothing was saved"
    : res.cancelled ? "Stopped early" : t.done;

  const summary = $("results-summary");
  summary.replaceChildren();
  const isCompress = state.tool === "compress-pdf" || state.tool === "compress-images";
  if (isCompress && ok.length) {
    const before = ok.reduce((s, r) => s + r.before, 0);
    const after = ok.reduce((s, r) => s + r.after, 0);
    const pct = before ? Math.round((1 - after / before) * 100) : 0;
    if (pct > 0) {
      summary.append(`${formatBytes(before)} → ${formatBytes(after)} · `, h("b", {}, `${pct}% smaller`));
    } else {
      summary.append("These files were already well optimized.");
    }
  } else if (ok.length === 1 && ok[0].pages != null) {
    const what = state.tool === "pdf-to-images" ? "image" : "page";
    summary.append(`${ok[0].pages} ${what}${ok[0].pages === 1 ? "" : "s"} · ${formatBytes(ok[0].after)}`);
  } else if (ok.length) {
    summary.append(`${ok.length} file${ok.length === 1 ? "" : "s"} saved`);
  }
  if (failed.length) summary.append(h("div", {}, `${failed.length} file${failed.length === 1 ? "" : "s"} could not be processed.`));
  if (res.cancelled) summary.append(h("div", {}, "You cancelled before every file was done."));

  $("open-folder").hidden = ok.length === 0;

  const list = $("results-list");
  list.replaceChildren(...items.map(resultRow));
}

function resultRow(r) {
  if (!r.ok) {
    return h("li", {},
      h("div", { class: "res-main" },
        h("div", { class: "res-name" }, basename(r.source || "")),
        h("div", { class: "res-sub err" }, r.error)),
      h("span", { class: "res-pill err" }, "Failed"));
  }
  let sub, pill, pillClass = "res-pill";
  if (state.tool === "compress-pdf" || state.tool === "compress-images") {
    const pct = Math.round((1 - r.after / r.before) * 100);
    sub = r.note ? r.note : `${formatBytes(r.before)} → ${formatBytes(r.after)}`;
    pill = pct > 0 ? `−${pct}%` : "0%";
    if (pct <= 0) pillClass += " neutral";
  } else if (state.tool === "pdf-to-images") {
    sub = `${r.pages} image${r.pages === 1 ? "" : "s"} · ${formatBytes(r.after)}`;
    pill = "Folder";
    pillClass += " neutral";
  } else {
    sub = `${r.pages} page${r.pages === 1 ? "" : "s"} · ${formatBytes(r.after)}`;
    pill = "PDF";
    pillClass += " neutral";
  }
  return h("li", {},
    h("div", { class: "res-main" },
      h("div", { class: "res-name" }, basename(r.output)),
      h("div", { class: "res-sub" }, sub)),
    h("span", { class: pillClass }, pill),
    h("button", { type: "button", class: "btn sm", onclick: () => api().open_path(r.output) }, "Open"),
    h("button", { type: "button", class: "btn ghost sm", onclick: () => api().reveal(r.output) }, "Show in folder"));
}

// --------------------------------------------------------------------------- actions

function switchTool(id) {
  if (state.running) {
    toast("Please wait for the current job to finish.");
    return;
  }
  state.tool = id;
  render();
}

async function browse() {
  if (state.running) return;
  const files = await api().pick_files(state.tool);
  addFiles(files);
}

async function addPaths(paths) {
  if (state.running) {
    toast("Please wait for the current job to finish.");
    return;
  }
  addFiles(await api().describe(paths));
}

function addFiles(files) {
  if (!files || !files.length) return;
  const t = tool();
  const list = state.files[state.tool];
  const have = new Set(list.map((f) => f.path.toLowerCase()));
  let wrongKind = 0, dupes = 0;
  for (const f of files) {
    if (f.kind !== t.kind) { wrongKind++; continue; }
    if (have.has(f.path.toLowerCase())) { dupes++; continue; }
    have.add(f.path.toLowerCase());
    list.push(f);
  }
  if (wrongKind) toast(`Skipped ${wrongKind} file${wrongKind === 1 ? "" : "s"} that ${wrongKind === 1 ? "isn't a" : "aren't"} ${t.kind === "pdf" ? "PDF" : "supported image"}${wrongKind === 1 ? "" : "s"}.`);
  if (dupes) toast(`Skipped ${dupes} file${dupes === 1 ? "" : "s"} already in the list.`);
  state.view[state.tool] = "files";
  render();
  loadThumbnails(list);
}

let thumbQueue = [];
let thumbWorkers = 0;

function loadThumbnails(files) {
  for (const f of files) {
    if (!thumbs.has(f.path)) {
      thumbs.set(f.path, "loading");
      thumbQueue.push(f.path);
    }
  }
  while (thumbWorkers < 4 && thumbQueue.length) thumbWorker();
}

async function thumbWorker() {
  thumbWorkers++;
  while (thumbQueue.length) {
    const path = thumbQueue.shift();
    try {
      thumbs.set(path, await api().thumbnail(path));
    } catch {
      thumbs.set(path, { thumb: null, pages: null });
    }
    if (!$("workspace").hidden && state.files[state.tool].some((f) => f.path === path)) renderFiles();
  }
  thumbWorkers--;
}

function removeFile(index) {
  state.files[state.tool].splice(index, 1);
  render();
}

async function run() {
  const id = state.tool;
  const files = state.files[id];
  if (state.running || files.length < (TOOLS[id].min || 1)) return;
  state.running = id;
  onProgress({ fraction: 0, message: "Starting…" });
  render();
  let res;
  try {
    res = await api().run(id, files.map((f) => f.path), { ...state.opts[id], outputDir: state.outDir[id] });
  } catch (e) {
    res = { error: String(e), results: [] };
  }
  state.running = null;

  if (res.error) toast(res.error, true);
  if (res.cancelled && !(res.results || []).length) toast("Cancelled.");
  if ((res.results || []).length) {
    state.results[id] = res;
    state.view[id] = "results";
  }
  if (state.tool === id) render();
}

function onProgress({ fraction, message }) {
  $("progress-fill").style.width = `${Math.round(fraction * 100)}%`;
  $("progress-msg").textContent = message;
}

function openResultFolder() {
  const ok = (state.results[state.tool].results || []).filter((r) => r.ok);
  if (ok.length) api().reveal(ok[0].output);
}

// --------------------------------------------------------------------------- wiring

function wire() {
  $("empty").addEventListener("click", browse);
  $("empty").addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); browse(); } });
  $("dz-browse").addEventListener("click", (e) => { e.stopPropagation(); browse(); });
  $("run").addEventListener("click", run);
  $("cancel").addEventListener("click", () => {
    $("progress-msg").textContent = "Cancelling…";
    api().cancel();
  });
  $("clear").addEventListener("click", () => { state.files[state.tool] = []; render(); });
  $("sort-az").addEventListener("click", () => {
    state.files[state.tool].sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: "base" }));
    renderFiles();
  });
  $("reverse").addEventListener("click", () => { state.files[state.tool].reverse(); renderFiles(); });
  $("outdir-change").addEventListener("click", async () => {
    const dir = await api().pick_folder();
    if (dir) { state.outDir[state.tool] = dir; renderOptions(); }
  });
  $("outdir-reset").addEventListener("click", () => { state.outDir[state.tool] = null; renderOptions(); });
  $("open-folder").addEventListener("click", openResultFolder);
  $("back").addEventListener("click", () => { state.view[state.tool] = "files"; render(); });
  $("restart").addEventListener("click", () => {
    state.files[state.tool] = [];
    state.view[state.tool] = "files";
    delete state.results[state.tool];
    render();
  });

  // Visual feedback for files dragged in from Explorer. The actual paths arrive
  // from Python (see _enable_file_drop in main.py), which calls app.addPaths.
  let depth = 0;
  const isFileDrag = (e) => e.dataTransfer && Array.from(e.dataTransfer.types || []).includes("Files");
  document.addEventListener("dragenter", (e) => {
    if (!isFileDrag(e)) return;
    depth++;
    $("drop-overlay").hidden = false;
  });
  document.addEventListener("dragleave", (e) => {
    if (!isFileDrag(e)) return;
    depth = Math.max(0, depth - 1);
    if (!depth) $("drop-overlay").hidden = true;
  });
  document.addEventListener("dragover", (e) => { if (isFileDrag(e)) e.preventDefault(); });
  document.addEventListener("drop", (e) => {
    depth = 0;
    $("drop-overlay").hidden = true;
    if (isFileDrag(e)) e.preventDefault();
  });
}

window.app = { addPaths, onProgress, state, addFiles, run };

wire();
render();
