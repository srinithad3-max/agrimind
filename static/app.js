/* AgriMind dashboard: vanilla JS, no build step, works offline (no chart CDN). */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const AG = {
  orchestrator: { name: "Orchestrator", icon: "⚙️", color: "var(--c-orchestrator)" },
  weather: { name: "Weather", icon: "🌦", color: "var(--c-weather)" },
  disease: { name: "Disease", icon: "🔬", color: "var(--c-disease)" },
  irrigation: { name: "Irrigation", icon: "💧", color: "var(--c-irrigation)" },
  yield: { name: "Yield", icon: "📈", color: "var(--c-yield)" },
  advisory: { name: "Advisory", icon: "🧑‍🌾", color: "var(--c-advisory)" },
};
const state = { lang: "en", result: null, meta: null, file: null, sample: null, partial: {} };
const fmt = (n, d = 0) => Number(n).toLocaleString("en-IN", { maximumFractionDigits: d, minimumFractionDigits: d });
const pct = (x, d = 0) => `${(x * 100).toFixed(d)}%`;
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const toast = (msg) => { const t = $("#toast"); t.textContent = msg; t.classList.add("on"); clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("on"), 3200); };
const isoDaysAgo = (n) => { const d = new Date(); d.setDate(d.getDate() - n); return d.toISOString().slice(0, 10); };

/* =============================== init =============================== */
async function init() {
  const [meta, health] = await Promise.all([
    fetch("/api/meta").then((r) => r.json()),
    fetch("/api/health").then((r) => r.json()).catch(() => null),
  ]);
  state.meta = meta;
  $("#crop").innerHTML = Object.entries(meta.crops).map(([k, c]) => `<option value="${k}">${c.name}</option>`).join("");
  $("#soil").innerHTML = Object.entries(meta.soils).map(([k, n]) => `<option value="${k}">${n}</option>`).join("");
  $("#place").innerHTML = Object.keys(meta.places).map((p) => `<option>${p}</option>`).join("");
  $("#samples").innerHTML = meta.samples.length
    ? meta.samples.map((s) => `<img src="/samples/${encodeURIComponent(s)}" data-s="${esc(s)}" title="${esc(s)}">`).join("")
    : `<small>Tip: put demo leaf photos in the <b>samples/</b> folder to get one-click samples here.</small>`;
  $("#sowing").value = isoDaysAgo(80);
  if (health) {
    const cnn = $("#pill-cnn");
    cnn.textContent = health.disease_model.ready ? `CNN ✓ ${health.disease_model.info}` : "CNN not trained · CV mode";
    cnn.className = "pill " + (health.disease_model.ready ? "ok" : "warn");
    $("#pill-yield").textContent = `Yield model R² ${health.yield_model.r2}`;
    $("#pill-yield").className = "pill ok";
    $("#pill-llm").textContent = health.llm ? "LLM ✓" : "LLM off · rules";
    $("#pill-llm").className = "pill " + (health.llm ? "ok" : "");
  }
  drawNetwork();
  bindForm();
  updateStagePreview();
}

/* =============================== form =============================== */
function bindForm() {
  const f = $("#farm");
  $("#moisture").oninput = (e) => ($("#mOut").textContent = e.target.value + "%");
  $("#crop").onchange = $("#sowing").onchange = updateStagePreview;
  $("#place").onchange = () => { $("#lat").value = ""; $("#lon").value = ""; };
  $("#placeSearch").onchange = async (e) => {
    const q = e.target.value.trim(); if (!q) return;
    const r = await fetch("/api/geocode?q=" + encodeURIComponent(q));
    const j = await r.json();
    if (j.error) return toast(j.error);
    const sel = $("#place");
    if (![...sel.options].some((o) => o.value === j.name)) sel.add(new Option(j.name, j.name, true, true));
    sel.value = j.name; $("#lat").value = j.lat; $("#lon").value = j.lon;
    toast(`Location set: ${j.name}`);
  };
  const drop = $("#drop"), file = $("#file");
  file.onchange = () => file.files[0] && setImage(file.files[0]);
  drop.ondragover = (e) => { e.preventDefault(); drop.classList.add("over"); };
  drop.ondragleave = () => drop.classList.remove("over");
  drop.ondrop = (e) => { e.preventDefault(); drop.classList.remove("over"); e.dataTransfer.files[0] && setImage(e.dataTransfer.files[0]); };
  $("#samples").onclick = (e) => {
    const img = e.target.closest("img"); if (!img) return;
    state.file = null; state.sample = img.dataset.s;
    $$("#samples img").forEach((i) => i.classList.toggle("on", i === img));
    $("#preview").src = img.src; drop.classList.add("has");
  };
  $$(".preset").forEach((b) => (b.onclick = () => applyPreset(b.dataset.preset)));
  $$(".lang button").forEach((b) => (b.onclick = () => {
    state.lang = b.dataset.lang;
    $$(".lang button").forEach((x) => x.classList.toggle("on", x === b));
    if (state.result) renderAdvisory(state.result.advisory, state.result.stage);
  }));
  f.onsubmit = (e) => { e.preventDefault(); run(); };
  $("#speakBtn").onclick = speak;
  $("#waBtn").onclick = whatsapp;
  $("#printBtn").onclick = () => window.print();
  $("#askForm").onsubmit = ask;
}

function setImage(fileObj) {
  state.file = fileObj; state.sample = null;
  $$("#samples img").forEach((i) => i.classList.remove("on"));
  $("#preview").src = URL.createObjectURL(fileObj);
  $("#drop").classList.add("has");
}

const PRESETS = {
  blight: { crop: "tomato", days: 80, area: 2, prev_crop: "potato", last_yield: 70, place: "Hyderabad", scenario: "blight",
    soil: "red", n: 220, p: 12, k: 150, ph: 6.9, moisture: 45, method: "sprinkler", sampleMatch: /tomato_early_blight/i },
  heat: { crop: "rice", days: 70, area: 3, prev_crop: "rice", last_yield: 15, place: "Nalgonda", scenario: "heat",
    soil: "black", n: 300, p: 18, k: 200, ph: 7.2, moisture: 75, method: "flood", sampleMatch: null },
  live: { crop: "tomato", days: 45, area: 1, prev_crop: "none", last_yield: "", place: "Hyderabad", scenario: "live",
    soil: "red", n: 280, p: 18, k: 220, ph: 6.8, moisture: 60, method: "drip", sampleMatch: null },
};
function applyPreset(key) {
  const p = PRESETS[key], f = $("#farm");
  $$(".preset").forEach((b) => b.classList.toggle("on", b.dataset.preset === key));
  for (const k of ["crop", "area", "prev_crop", "last_yield", "place", "scenario", "soil", "n", "p", "k", "ph", "moisture"]) f.elements[k].value = p[k];
  $("#mOut").textContent = p.moisture + "%";
  $("#sowing").value = isoDaysAgo(p.days);
  f.querySelector(`input[name=method][value=${p.method}]`).checked = true;
  $("#lat").value = ""; $("#lon").value = "";
  state.file = null; state.sample = null; $("#drop").classList.remove("has");
  $$("#samples img").forEach((i) => i.classList.remove("on"));
  if (p.sampleMatch) {
    const img = $$("#samples img").find((i) => p.sampleMatch.test(i.dataset.s));
    if (img) img.click();
  }
  updateStagePreview();
  toast(`Scenario loaded. Press "Run agent team"`);
}

async function updateStagePreview() {
  const crop = $("#crop").value, sow = $("#sowing").value;
  if (!crop || !sow) return;
  const s = await fetch(`/api/stage?crop=${crop}&sowing_date=${sow}`).then((r) => r.json());
  $("#stagePreview").textContent = s.past_harvest
    ? `Day ${s.das}: season complete (harvest window passed)`
    : `Day ${s.das} · ${s.name} · ${s.days_to_harvest} days to harvest`;
}

/* =============================== run =============================== */
async function run() {
  const btn = $("#runBtn"); btn.disabled = true; btn.firstElementChild.textContent = "Agents working…";
  resetViews();
  const fd = new FormData($("#farm"));
  fd.set("lang", state.lang);
  if (!fd.get("lat")) { fd.delete("lat"); fd.delete("lon"); }
  if (state.file) fd.set("image", state.file); else fd.delete("image");
  if (state.sample) fd.set("sample", state.sample);
  try {
    const res = await fetch("/api/analyze", { method: "POST", body: fd });
    if (!res.ok) throw new Error(`Server error ${res.status}`);
    const reader = res.body.getReader(), dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
        if (line) handle(JSON.parse(line));
      }
    }
  } catch (err) {
    console.error(err); toast("Run failed: " + err.message);
  } finally {
    btn.disabled = false; btn.firstElementChild.textContent = "Run agent team";
    $("#liveDot").classList.remove("on"); $("#liveDot").textContent = "done";
  }
}

function resetViews() {
  state.partial = {};
  $("#feed").innerHTML = "";
  $("#liveDot").classList.add("on"); $("#liveDot").textContent = "live";
  $("#runtime").textContent = "";
  $$("#net .node").forEach((n) => { n.classList.remove("running", "done"); $(".st", n).textContent = "waiting"; });
  $$("#net .spoke").forEach((s) => s.classList.remove("on"));
  $("#hubFacts").textContent = "0 facts";
}

let factCount = 0;
function handle(e) {
  switch (e.type) {
    case "start": factCount = 0; break;
    case "fact": factCount++; $("#hubFacts").textContent = `${factCount} facts`; break;
    case "message": addFeed(e); animatePacket(e.sender, e.to); break;
    case "agent_start": setNode(e.agent, "running", "thinking…"); break;
    case "agent_done":
      setNode(e.agent, "done", `${e.ms} ms ✓`);
      state.partial[e.agent] = e.output;
      if (e.agent === "weather") renderWeather(e.output);
      if (e.agent === "disease") renderDisease(e.output);
      if (e.agent === "irrigation") renderIrrigation(e.output);
      if (e.agent === "yield") renderYield(e.output);
      break;
    case "final":
      state.result = e.result;
      renderStage(e.result.stage);
      renderAdvisory(e.result.advisory, e.result.stage);
      renderKPIs(e.result);
      $("#runtime").textContent = `5 agents · ${e.result.log.length} messages · ${(e.result.runtime_ms / 1000).toFixed(1)} s`;
      setTimeout(() => $("#advisoryCard").scrollIntoView({ behavior: "smooth", block: "start" }), 400);
      break;
    case "error": toast(`${e.agent} agent error: ${e.error}`); setNode(e.agent, "", "error"); break;
  }
}

function addFeed(e) {
  const a = AG[e.sender] || AG.orchestrator, to = e.to && e.to !== "all" ? AG[e.to] : null;
  const li = document.createElement("li");
  li.className = e.level;
  li.innerHTML = `<span class="who" style="background:${a.color}">${a.icon} ${a.name}</span>
    <div class="msg">${to ? `<span class="to">→ ${to.name}</span>` : ""}${esc(e.text)}</div>`;
  const feed = $("#feed"); feed.appendChild(li); feed.scrollTop = feed.scrollHeight;
}

/* =========================== agent network =========================== */
const POS = {};
function drawNetwork() {
  const svg = $("#net"), cx = 260, cy = 165, R = 128;
  const ids = ["weather", "disease", "irrigation", "yield", "advisory"];
  ids.forEach((id, i) => {
    const ang = -Math.PI / 2 + (i * 2 * Math.PI) / ids.length;
    POS[id] = [cx + R * 1.45 * Math.cos(ang), cy + R * Math.sin(ang)];
  });
  POS.orchestrator = [cx, cy]; POS.all = [cx, cy];
  let html = ids.map((id) => `<line class="spoke" id="sp-${id}" x1="${cx}" y1="${cy}" x2="${POS[id][0]}" y2="${POS[id][1]}" style="stroke:${AG[id].color}"/>`).join("");
  html += `<g class="hub"><rect x="${cx - 62}" y="${cy - 26}" width="124" height="52" rx="12"/>
    <text x="${cx}" y="${cy - 4}">SHARED BLACKBOARD</text><text class="facts" id="hubFacts" x="${cx}" y="${cy + 13}">0 facts</text></g>`;
  html += ids.map((id) => {
    const [x, y] = POS[id], a = AG[id];
    return `<g class="node" id="nd-${id}" style="color:${a.color}">
      <circle class="ring" cx="${x}" cy="${y}" r="30" style="stroke:${a.color}"/>
      <circle class="bg" cx="${x}" cy="${y}" r="29" style="stroke:${a.color}"/>
      <text class="ic" x="${x}" y="${y + 8}">${a.icon}</text>
      <text class="lb" x="${x}" y="${y + 46}">${a.name}</text>
      <text class="st" x="${x}" y="${y + 59}">waiting</text></g>`;
  }).join("");
  html += `<g id="packets"></g>`;
  svg.innerHTML = html;
}
function setNode(id, cls, label) {
  const n = $("#nd-" + id); if (!n) return;
  n.classList.remove("running", "done"); if (cls) n.classList.add(cls);
  $(".st", n).textContent = label;
  if (cls === "done") $("#sp-" + id)?.classList.add("on");
}
function animatePacket(from, to) {
  const a = POS[from] || POS.orchestrator, b = POS[to] || POS.all;
  if (a === b) return;
  const g = $("#packets"), color = (AG[from] || AG.orchestrator).color;
  const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  dot.setAttribute("r", 6); dot.setAttribute("class", "packet"); dot.style.fill = color; dot.style.color = color;
  g.appendChild(dot);
  const mx = (a[0] + b[0]) / 2 + (a[1] - b[1]) * 0.25, my = (a[1] + b[1]) / 2 + (b[0] - a[0]) * 0.25;
  const t0 = performance.now(), dur = 650;
  (function step(now) {
    const t = Math.min(1, (now - t0) / dur), u = 1 - t;
    dot.setAttribute("cx", u * u * a[0] + 2 * u * t * mx + t * t * b[0]);
    dot.setAttribute("cy", u * u * a[1] + 2 * u * t * my + t * t * b[1]);
    if (t < 1) requestAnimationFrame(step); else dot.remove();
  })(t0);
}

/* =============================== charts =============================== */
/* Minimal SVG chart: series = [{type:'bar'|'line', values, color, label, dash}] */
function chart({ labels, series, height = 170, yMax, yLabel = "", y2, width = 520 }) {
  const W = width, H = height, L = 34, Rm = y2 ? 34 : 8, T = 18, B = 24, w = W - L - Rm, h = H - T - B;
  const prim = series.filter((s) => !s.axis2);
  const maxV = yMax ?? Math.max(1, ...prim.flatMap((s) => s.stack ? [] : s.values), ...stackTotals(prim, labels.length)) * 1.12;
  const y = (v) => T + h - (v / maxV) * h, n = labels.length, bw = w / n;
  let out = `<svg class="chart" viewBox="0 0 ${W} ${H}">`;
  for (let i = 0; i <= 4; i++) {
    const v = (maxV * i) / 4;
    out += `<line class="grid" x1="${L}" x2="${W - Rm}" y1="${y(v)}" y2="${y(v)}"/><text x="${L - 6}" y="${y(v) + 3}" text-anchor="end">${fmt(v, maxV < 5 ? 1 : 0)}</text>`;
  }
  if (yLabel) out += `<text x="${L - 6}" y="8" text-anchor="end">${yLabel}</text>`;
  const bars = prim.filter((s) => s.type === "bar" && !s.stack), stacks = prim.filter((s) => s.stack);
  const groups = bars.length + (stacks.length ? 1 : 0), gw = (bw * 0.7) / Math.max(1, groups);
  labels.forEach((lb, i) => {
    const x0 = L + i * bw + bw * 0.15;
    bars.forEach((s, j) => { const v = s.values[i] || 0; out += `<rect x="${x0 + j * gw}" y="${y(v)}" width="${gw - 2}" height="${T + h - y(v)}" rx="3" fill="${s.color}"><title>${s.label}: ${fmt(v, 1)}</title></rect>`; });
    let acc = 0;
    stacks.forEach((s) => { const v = s.values[i] || 0; if (!v) return; out += `<rect x="${x0 + bars.length * gw}" y="${y(acc + v)}" width="${gw - 2}" height="${y(acc) - y(acc + v)}" rx="3" fill="${s.color}"><title>${s.label}: ${fmt(v, 1)}</title></rect>`; acc += v; });
    out += `<text x="${L + i * bw + bw / 2}" y="${H - 6}" text-anchor="middle">${esc(lb)}</text>`;
  });
  const line = (s, sy) => {
    const pts = s.values.map((v, i) => `${L + i * bw + bw / 2},${sy(v)}`).join(" ");
    return `<polyline points="${pts}" fill="none" stroke="${s.color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" ${s.dash ? 'stroke-dasharray="5 4"' : ""}/>` +
      s.values.map((v, i) => s.dots === false ? "" : `<circle cx="${L + i * bw + bw / 2}" cy="${sy(v)}" r="3" fill="${s.color}"><title>${s.label}: ${fmt(v, 1)}</title></circle>`).join("");
  };
  prim.filter((s) => s.type === "line").forEach((s) => (out += line(s, y)));
  if (y2) {
    const y2f = (v) => T + h - ((v - y2.min) / (y2.max - y2.min)) * h;
    series.filter((s) => s.axis2).forEach((s) => (out += line(s, y2f)));
    for (let i = 0; i <= 4; i++) { const v = y2.min + ((y2.max - y2.min) * i) / 4; out += `<text x="${W - Rm + 6}" y="${y2f(v) + 3}">${fmt(v)}${y2.unit || ""}</text>`; }
  }
  return out + "</svg>";
}
function stackTotals(series, n) {
  const st = series.filter((s) => s.stack); if (!st.length) return [0];
  return Array.from({ length: n }, (_, i) => st.reduce((a, s) => a + (s.values[i] || 0), 0));
}
const legend = (items) => `<div class="legend">${items.map(([c, l]) => `<span><i style="background:${c}"></i>${l}</span>`).join("")}</div>`;

/* =============================== renderers =============================== */
const WMO = (c) => c === 0 ? "☀️" : c <= 2 ? "🌤" : c === 3 ? "☁️" : c <= 48 ? "🌫" : c <= 57 ? "🌦" : c <= 67 ? "🌧" : c <= 77 ? "🌨" : c <= 82 ? "🌧" : "⛈";

function renderWeather(w) {
  const card = $("#weatherCard"), d = w.daily, s = w.summary;
  $("#wxSource").textContent = s.source;
  card.innerHTML = card.firstElementChild.outerHTML + `
    <div class="wx-days">${d.map((x) => `<div class="wx-day ${x.heat ? "hot" : x.fungal ? "fungal" : ""}" title="RH ${x.rh}% · wind ${x.wind} km/h · ET₀ ${x.et0} mm">
      <div class="d">${x.day}</div><div class="ico">${WMO(x.code)}</div><div class="t">${Math.round(x.tmax)}°<small>/${Math.round(x.tmin)}°</small></div>
      <div class="r">${x.rain ? x.rain.toFixed(0) + " mm" : "–"}</div><small>${x.rain_prob}%</small></div>`).join("")}</div>
    ${chart({ labels: d.map((x) => x.day.slice(0, 3)), height: 150, yLabel: "mm",
      series: [{ type: "bar", values: d.map((x) => x.rain), color: "var(--water)", label: "Rain mm" },
               { type: "line", values: d.map((x) => x.et0), color: "var(--sun)", label: "ET₀ mm" },
               { type: "line", axis2: true, values: d.map((x) => x.rh), color: "var(--violet)", label: "Humidity %", dash: true }],
      y2: { min: 0, max: 100, unit: "%" } })}
    ${legend([["var(--water)", "Rain (mm)"], ["var(--sun)", "ET₀ evapotranspiration (mm)"], ["var(--violet)", "Humidity (%)"]])}
    <div class="risks">${w.risks.length ? w.risks.map((r) => `<span class="risk ${r.level}">${esc(r.text)}</span>`).join("") : `<span class="risk low">No major weather risks this week</span>`}</div>`;
}

function renderDisease(dz) {
  const card = $("#diseaseCard");
  const head = `<div class="card-h"><h2>🔬 Disease</h2><div class="tabs" id="imgTabs"></div></div>`;
  if (!dz.has_image) {
    card.innerHTML = head + `<div class="empty">No leaf photo. Weather-based disease risk: <b>${dz.risk_level.toUpperCase()}</b>.<br>Upload a photo for CNN diagnosis + severity.</div>`;
    return;
  }
  const imgs = [["Photo", dz.original], ["Lesion map", dz.overlay]];
  if (dz.gradcam) imgs.push(["Grad-CAM", dz.gradcam]);
  const sevCol = dz.healthy ? "var(--green)" : "var(--danger)";
  card.innerHTML = head + `
    <div class="dz">
      <div><img id="dzImg" src="${dz.gradcam || dz.overlay}" alt="leaf analysis"></div>
      <div>
        <div class="dx-name" style="color:${sevCol}">${esc(dz.name)}</div>
        <div class="dx-sub">${dz.method === "cnn" ? `CNN · ${pct(dz.confidence)} confidence · ${esc(dz.plant)}` : "OpenCV colour-texture analysis (CNN not loaded)"} · ${esc(dz.pathogen)}</div>
        <small>Leaf area affected · ${dz.lesion_count} lesions</small>
        <div class="meter"><i style="width:${Math.max(2, dz.severity * 100)}%"></i></div>
        <b>${pct(dz.severity, 1)}</b> <small>(${dz.severity_band})</small>
        ${dz.top?.length ? `<div class="topk">${dz.top.map((t) => `<div><span class="lbl">${esc(t.label.replace(/___/g, " · ").replace(/_/g, " "))}</span><span>${pct(t.prob, 1)}</span><span class="b"><i style="width:${t.prob * 100}%"></i></span></div>`).join("")}</div>` : ""}
      </div>
    </div>
    ${dz.healthy ? "" : `<p style="margin:12px 0 2px;font-weight:700;font-size:12.5px">Projected spread over the forecast week</p>
    ${chart({ labels: ["Now", ...(state.partial.weather?.daily || []).map((x) => x.day.slice(0, 3))], height: 120, yLabel: "% leaf",
      series: [{ type: "line", values: dz.spread_untreated.map((v) => v * 100), color: "var(--danger)", label: "Untreated" },
               { type: "line", values: dz.spread_treated.map((v) => v * 100), color: "var(--green-2)", label: "Treated", dash: true }] })}
    ${legend([["var(--danger)", "If untreated"], ["var(--green-2)", "With treatment"]])}`}
    ${(dz.notes || []).map((n) => `<div class="note">⚠️ ${esc(n)}</div>`).join("")}`;
  const tabs = $("#imgTabs", card);
  tabs.innerHTML = imgs.map(([l], i) => `<button class="${i === imgs.length - 1 ? "on" : ""}">${l}</button>`).join("");
  $$("button", tabs).forEach((b, i) => (b.onclick = () => { $("#dzImg").src = imgs[i][1]; $$("button", tabs).forEach((x) => x.classList.toggle("on", x === b)); }));
}

function renderIrrigation(ir) {
  const card = $("#irrCard"), s = ir.schedule;
  $("#irrMeta").textContent = `${ir.soil} · ${ir.method_recommended}${ir.method_recommended !== ir.method ? ` (was ${ir.method})` : ""}`;
  const depl = s.map((r) => r.depletion_pct * 100), deplNone = s.map((r) => r.depletion_none_pct * 100);
  const thr = ir.taw ? (ir.raw / ir.taw) * 100 : null;
  card.innerHTML = card.firstElementChild.outerHTML + `
    ${chart({ labels: s.map((r) => r.day.slice(0, 3)), height: 160, yLabel: "mm/day",
      series: [{ type: "bar", values: s.map((r) => r.etc), color: "var(--sun)", label: "Crop water use ETc" },
               { type: "bar", stack: true, values: s.map((r) => r.eff_rain), color: "var(--water)", label: "Effective rain" },
               { type: "bar", stack: true, values: s.map((r) => r.gross_mm), color: "var(--teal)", label: "Irrigation" },
               { type: "line", axis2: true, values: deplNone, color: "var(--danger)", label: "Soil dryness, no irrigation %", dash: true },
               { type: "line", axis2: true, values: depl, color: "var(--green)", label: "Soil dryness with plan %" }],
      y2: { min: 0, max: 100, unit: "%" } })}
    ${legend([["var(--sun)", "ETc crop use"], ["var(--water)", "Rain"], ["var(--teal)", "Planned irrigation"], ["var(--green)", "Root-zone depletion · plan"], ["var(--danger)", "· no irrigation"]])}
    ${thr ? `<small>Stress threshold (RAW) = ${thr.toFixed(0)}% depletion · TAW ${ir.taw} mm</small>` : ""}
    <div class="stats">
      <div class="stat"><span>Water to apply</span><b>${fmt(ir.total_litres / 1000)} kL</b></div>
      <div class="stat"><span>vs flood calendar</span><b style="color:var(--green)">−${pct(ir.water_saved_pct)}</b></div>
      <div class="stat"><span>Best time</span><b style="font-size:13px">${esc(ir.best_time)}</b></div>
    </div>
    ${(ir.notes || []).map((n) => `<div class="note" style="background:#EEF6F6;border-color:#BFE0DF">💧 ${esc(n)}</div>`).join("")}`;
}

function renderYield(y) {
  const card = $("#yieldCard"), max = y.potential.q_acre || 1;
  $("#yMeta").textContent = `quintal / acre`;
  const row = (lbl, v, col, extra = "") => `<div class="row"><span>${lbl}</span><div class="track"><i style="width:${(v.q_acre / max) * 100}%;background:${col}"></i></div><span class="v">${fmt(v.q_acre, 1)} ${extra}</span></div>`;
  const a = y.attribution, m = y.model;
  card.innerHTML = card.firstElementChild.outerHTML + `
    <div class="scen">
      ${row("Potential", y.potential, "#A9C9B2")}
      ${row("No action", y.no_action, "var(--danger)", `<small>${pct(y.no_action.change_pct)}</small>`)}
      ${row("With AgriMind", y.with_plan, "var(--green)", `<small>${pct(y.with_plan.change_pct)}</small>`)}
      ${y.last_yield_q_acre ? `<div class="row"><span>Last season</span><div class="track"><i style="width:${Math.min(100, (y.last_yield_q_acre / max) * 100)}%;background:#C9C2AC"></i></div><span class="v">${fmt(y.last_yield_q_acre, 1)}</span></div>` : ""}
    </div>
    <p style="margin:14px 0 0;font-weight:700;font-size:12.5px">Where the "no action" loss comes from</p>
    <div class="attr"><i style="width:${a.disease * 100 / Math.max(0.0001, a.disease + a.water) * Math.min(1, (a.disease + a.water) * 2)}%;background:var(--danger)"></i><i style="width:${a.water * 100 / Math.max(0.0001, a.disease + a.water) * Math.min(1, (a.disease + a.water) * 2)}%;background:var(--water)"></i></div>
    ${legend([["var(--danger)", `Disease ${pct(a.disease, 1)}`], ["var(--water)", `Water stress ${pct(a.water, 1)}`]])}
    <div class="stats">
      <div class="stat"><span>Saved by plan</span><b>${fmt(y.saved_quintals, 1)} q</b></div>
      <div class="stat"><span>Value</span><b style="color:var(--green)">₹${fmt(y.revenue_protected)}</b></div>
      <div class="stat"><span>${y.vs_last_season_pct != null ? "vs last season" : "Price used"}</span><b>${y.vs_last_season_pct != null ? (y.vs_last_season_pct >= 0 ? "+" : "") + pct(y.vs_last_season_pct) : "₹" + fmt(y.price_per_q) + "/q"}</b></div>
    </div>
    <div class="modelcard">Model: ${m.algorithm} · R² ${m.r2} on ${fmt(m.n_test)} held-out samples · top drivers: ${m.importance.slice(0, 4).map((t) => t[0].replace("_", " ")).join(", ")}</div>`;
}

function renderStage(s) {
  const card = $("#stageCard"), cols = ["#9BC53D", "#2F8F5B", "#D9921F", "#8C6B3E"];
  const pos = Math.min(100, (s.das / s.total_days) * 100);
  const kcLabels = s.kc_curve.map((_, i) => (i * 5) % 20 === 0 ? `d${i * 5}` : "");
  card.innerHTML = card.firstElementChild.outerHTML + `
    <div class="timeline">${s.stages.map((st, i) => `<div style="flex:${st.days};background:${cols[i]};opacity:${i === s.index ? 1 : 0.55}">${esc(st.name)}</div>`).join("")}
      <span class="marker" style="left:${pos}%"><span>Today · day ${s.das}</span></span></div>
    ${chart({ labels: kcLabels, height: 150, width: 1100, yMax: 1.4, series: [{ type: "line", values: s.kc_curve, color: "var(--green)", label: "Kc", dots: false }] })}
    <small>Crop coefficient Kc rises with canopy growth and peaks at flowering: the stage where water and heat stress cost the most yield. Today Kc = <b>${s.kc.toFixed(2)}</b>, ${s.days_to_harvest} days to harvest.</small>`;
}

const SRC = (id) => `<span class="src" title="${AG[id]?.name} Agent" style="background:${AG[id]?.color}">${AG[id]?.icon}</span>`;
function renderAdvisory(adv, stage) {
  const L = state.lang;
  $("#advStage").textContent = `· ${stage.name}, day ${stage.das}`;
  const ai = $("#aiSummary");
  if (adv.ai_summary) { ai.hidden = false; ai.textContent = "🤖 " + adv.ai_summary; } else ai.hidden = true;
  $("#recs").innerHTML = adv.recommendations.map((r, i) => `
    <div class="rec p${r.priority}" style="animation-delay:${i * 60}ms">
      <span class="bar"></span>
      <div><h3>${esc(r.title[L] || r.title.en)}</h3>
        ${L !== "en" ? `<p class="why" style="margin-top:2px">${esc(r.title.en)}</p>` : ""}
        <p>${esc(r.detail)}</p><p class="why"><b>Why:</b> ${esc(r.why)}</p></div>
      <div class="meta"><span class="badge">${r.priority_label}</span><span class="srcs">${r.sources.map(SRC).join("")}</span></div>
    </div>`).join("") || `<p class="empty">No actions needed: the crop is on track.</p>`;
}

function renderKPIs(r) {
  const set = (k, b, s, cls = "") => { const el = $(`.kpi[data-k=${k}]`); el.className = `kpi ${cls} ${k === "money" ? "accent" : ""}`; $("b", el).textContent = b; $("small", el).textContent = s; };
  const st = r.stage, d = r.disease, ir = r.irrigation, y = r.yield;
  set("stage", st.name, `Day ${st.das} · ${st.days_to_harvest} d to harvest`);
  if (d.has_image) set("disease", d.healthy ? "Healthy" : d.name, d.healthy ? "No symptoms" : `${pct(d.severity)} of leaf · ${d.pathogen}`, d.healthy ? "good" : "bad");
  else set("disease", `Risk: ${d.risk_level}`, "No photo · weather screening", d.risk_level === "high" ? "bad" : "");
  set("water", `${fmt(ir.total_litres / 1000)} kL`, `${ir.schedule.filter((x) => x.status === "irrigate").length} irrigation(s) · −${pct(ir.water_saved_pct)} water`);
  set("yield", `${fmt(y.with_plan.q_acre, 1)} q/ac`, `No action: ${pct(y.no_action.change_pct)} · plan: ${pct(y.with_plan.change_pct)}`, y.no_action.change_pct < -0.1 ? "bad" : "good");
  set("money", `₹${fmt(y.revenue_protected)}`, `${fmt(y.saved_quintals, 1)} quintals on ${r.context.area} acre(s)`);
}

/* =========================== voice / share / ask =========================== */
function planText() {
  const r = state.result; if (!r) return "";
  const L = state.lang, recs = r.advisory.recommendations.slice(0, 5);
  if (r.advisory.ai_summary && r.advisory.ai_lang === L) return r.advisory.ai_summary;
  return recs.map((x, i) => `${i + 1}. ${x.title[L] || x.title.en}`).join(". ");
}
function speak() {
  if (!state.result) return toast("Run the agents first");
  if (!("speechSynthesis" in window)) return toast("Voice not supported in this browser");
  speechSynthesis.cancel();
  const code = { en: "en-IN", hi: "hi-IN", te: "te-IN" }[state.lang];
  const u = new SpeechSynthesisUtterance(planText());
  const voices = speechSynthesis.getVoices();
  const v = voices.find((x) => x.lang === code) || voices.find((x) => x.lang.startsWith(state.lang));
  if (v) u.voice = v; else if (state.lang !== "en") toast(`No ${state.lang === "te" ? "Telugu" : "Hindi"} voice installed; trying system default`);
  u.lang = code; u.rate = 0.95;
  speechSynthesis.speak(u);
}
function whatsapp() {
  if (!state.result) return toast("Run the agents first");
  const r = state.result, L = state.lang;
  const head = `🌾 AgriMind · ${r.context.crop} · ${r.stage.name} (day ${r.stage.das})`;
  const body = r.advisory.recommendations.slice(0, 5).map((x) => `${x.priority === 1 ? "🔴" : x.priority === 2 ? "🟠" : "🔵"} ${x.title[L] || x.title.en}`).join("\n");
  window.open("https://wa.me/?text=" + encodeURIComponent(`${head}\n\n${body}\n\nYield protected: ₹${fmt(r.yield.revenue_protected)}`), "_blank");
}
async function ask(e) {
  e.preventDefault();
  const q = $("#askQ").value.trim(); if (!q) return;
  const r = state.result;
  $("#askA").textContent = "Thinking…";
  const context = r ? {
    crop: r.context.crop, stage: r.stage.name, das: r.stage.das, weather: r.weather.summary, risks: r.weather.risks.map((x) => x.text),
    disease: { name: r.disease.name, severity: r.disease.severity, treatment: r.disease.chemical },
    irrigation: r.irrigation.schedule.map(({ day, status, gross_mm }) => ({ day, status, gross_mm })),
    yield: { no_action: r.yield.no_action, with_plan: r.yield.with_plan }, recommendations: r.advisory.recommendations,
  } : {};
  const res = await fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q, context, lang: state.lang }) }).then((x) => x.json());
  $("#askA").textContent = res.answer;
}

init();
