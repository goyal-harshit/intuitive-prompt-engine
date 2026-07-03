/* GestureGPT frontend — plain ES modules, no build step.
   WebSocket contract is identical for the future React/Vite client. */

const $ = (id) => document.getElementById(id);
let ws = null, sessionId = null, paused = false, videoOn = false;

// Dynamic backend URL configuration
function getBackendUrl() {
  if (location.hostname === "localhost" || location.hostname === "127.0.0.1") {
    return "";
  }
  const saved = localStorage.getItem("backend_url");
  if (saved) return saved.replace(/\/$/, "");
  return "http://localhost:8000";
}

function getWsUrl() {
  const backend = getBackendUrl();
  if (!backend) {
    return `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}`;
  }
  return backend.replace(/^http/, "ws");
}

const FEATURE_KEYS = ["openness", "separation", "expansion_rate", "verticality",
  "circularity", "tempo", "smoothness", "stillness", "valence", "arousal"];

// Settings Modal UI Handlers
$("btn-settings").onclick = () => {
  $("input-backend-url").value = localStorage.getItem("backend_url") || "http://localhost:8000";
  $("settings-modal").hidden = false;
};
$("settings-close").onclick = $("btn-settings-cancel").onclick = () => {
  $("settings-modal").hidden = true;
};
$("settings-modal").querySelector(".modal-backdrop").onclick = () => {
  $("settings-modal").hidden = true;
};
$("btn-settings-save").onclick = () => {
  let val = $("input-backend-url").value.trim();
  if (val) {
    if (!/^https?:\/\//i.test(val)) val = "http://" + val;
    localStorage.setItem("backend_url", val);
  } else {
    localStorage.removeItem("backend_url");
  }
  $("settings-modal").hidden = true;
};

$("btn-start").onclick = startSession;
$("btn-stop").onclick = stopSession;
$("btn-pause").onclick = togglePause;
$("btn-reset").onclick = () => send({ type: "reset_scene" });
$("banner-close").onclick = hideBanner;
$("btn-help").onclick = () => { $("help-modal").hidden = false; };
$("help-close").onclick = () => { $("help-modal").hidden = true; };
$("help-modal").querySelector(".modal-backdrop").onclick = () => { $("help-modal").hidden = true; };
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    $("help-modal").hidden = true;
    $("settings-modal").hidden = true;
  }
});

async function startSession() {
  hideBanner();
  setStatus("connecting…", "busy");
  $("btn-start").disabled = true;
  const backend = getBackendUrl();
  if (sessionId) { await fetch(`${backend}/api/session/${sessionId}`, { method: "DELETE" }).catch(() => {}); }
  const r = await fetch(`${backend}/api/session`, { method: "POST" }).catch(() => null);
  if (!r || !r.ok) { setStatus("backend error", "err"); $("btn-start").disabled = false; return; }
  sessionId = (await r.json()).session_id;
  connect();
  startVideo();
  $("btn-stop").disabled = $("btn-pause").disabled = $("btn-reset").disabled = false;
}

async function stopSession() {
  const id = sessionId;
  sessionId = null;
  stopVideo();
  if (ws) { try { ws.close(); } catch {} ws = null; }
  const backend = getBackendUrl();
  if (id) { await fetch(`${backend}/api/session/${id}`, { method: "DELETE" }).catch(() => {}); }
  paused = false;
  $("btn-pause").textContent = "Pause";
  $("btn-start").disabled = false;
  $("btn-stop").disabled = $("btn-pause").disabled = $("btn-reset").disabled = true;
  setStatus("disconnected", "err");
}

/* ---- live camera: poll the latest annotated frame in an onload loop ---- */
function startVideo() {
  videoOn = true;
  const v = $("video");
  v.hidden = false;
  $("camera-idle").hidden = true;
  const tag = $("cam-tag"); tag.textContent = "live"; tag.className = "tag live";
  v.onload = () => { if (videoOn) requestAnimationFrame(pumpFrame); };
  v.onerror = () => { if (videoOn) setTimeout(pumpFrame, 250); };
  pumpFrame();
}

function pumpFrame() {
  if (!videoOn || !sessionId) return;
  $("video").src = `${getBackendUrl()}/api/session/${sessionId}/frame?t=${Date.now()}`;
}

function stopVideo() {
  videoOn = false;
  const v = $("video");
  v.onload = v.onerror = null;
  v.hidden = true;
  v.removeAttribute("src");
  $("camera-idle").hidden = false;
  const tag = $("cam-tag"); tag.textContent = "offline"; tag.className = "tag";
}

function connect() {
  ws = new WebSocket(`${getWsUrl()}/ws/${sessionId}`);
  ws.onopen = () => setStatus("live", "ok");
  ws.onclose = () => { if (sessionId) setStatus("disconnected", "err"); };
  ws.onerror = () => setStatus("connection error", "err");
  ws.onmessage = (e) => handle(JSON.parse(e.data));
}

function send(msg) { if (ws && ws.readyState === 1) ws.send(JSON.stringify(msg)); }

function togglePause() {
  paused = !paused;
  send({ type: paused ? "pause" : "resume" });
  $("btn-pause").textContent = paused ? "Resume" : "Pause";
}

function handle({ type, data }) {
  switch (type) {
    case "features":
      if (!$("banner").hidden && !$("banner").classList.contains("warn")) hideBanner();
      renderFeatures(data); break;
    case "primitive": prepend("primitives",
      `<b>${data.primitive}</b> · ${(data.confidence * 100) | 0}% · ${data.params.duration_s}s`); break;
    case "intent": data.forEach((f) => prepend("intents",
      `<b>${f.attribute}</b> → ${f.value} <span class="muted">(${f.confidence}${f.modifiers.length ? ", " + f.modifiers.join(", ") : ""})</span>`)); break;
    case "scene_update": renderScene(data); break;
    case "generation_started":
      showGenerating(true);
      $("prompt").textContent = data.positive; break;
    case "generation_done":
      showGenerating(false);
      $("image").src = getBackendUrl() + data.url + "?t=" + Date.now();
      $("image").hidden = false;
      $("gen-status").hidden = true;
      $("prompt").textContent = `${data.prompt}  ·  ${data.backend}, ${data.latency_ms} ms`; break;
    case "status":
      setCompleteness(data.completeness);
      if (data.generating) setStatus("generating…", "busy");
      else setStatus(paused ? "paused" : "live", paused ? "busy" : "ok"); break;
    case "error":
      setStatus(`${data.code}`, "err");
      prepend("intents", `<span class="err">${data.code}: ${data.message}</span>`);
      if (data.code === "CAMERA_UNAVAILABLE") {
        stopVideo();
        showBanner("Camera unavailable",
          `GestureGPT couldn't open your webcam. Close any other app that may be using it ` +
          `(Zoom, Teams, Camera), then click <b>Start session</b> again. On Windows also check ` +
          `<b>Settings → Privacy &amp; security → Camera → “Let desktop apps access your camera.”</b>`,
          false);
      } else if (data.code === "BACKEND_DOWN") {
        showBanner("Image backend error",
          `The image generator didn't respond: ${escapeHtml(data.message)}. ` +
          `Check your internet connection — the pipeline keeps running and will retry.`,
          true);
      }
      break;
  }
}

function showGenerating(on) {
  $("gen-badge").hidden = !on;
  const spinner = document.querySelector("#gen-status .spinner");
  if (spinner) spinner.hidden = !on;
  const ph = $("gen-status");
  if (on) { ph.hidden = false; ph.querySelector("p").textContent = "Rendering your scene…"; }
}

function renderFeatures(f) {
  $("features").innerHTML = FEATURE_KEYS.map((k) => {
    const v = f[k] ?? 0;
    const pct = Math.min(100, Math.max(0, (k === "valence" ? (v + 1) / 2 : Math.abs(v)) * 100));
    return `<div class="feat"><label>${k.replace(/_/g, " ")}</label>
      <div class="bar"><div style="width:${pct}%"></div></div>
      <span>${v.toFixed(2)}</span></div>`;
  }).join("") + `<div class="feat"><label>hands</label>
      <div class="bar"><div style="width:${f.hands_visible ? 100 : 0}%"></div></div>
      <span>${f.hands_visible}</span></div>`;
}

function renderScene(g) {
  const objs = Object.values(g.objects || {});
  const globals = Object.entries(g.globals || {});
  let html = "";
  if (objs.length) {
    html += "<h3>Objects</h3>" + objs.map((o) =>
      `<div class="node"><b>${o.category}</b> <span class="muted">salience ${o.salience.toFixed(2)}</span>
       ${Object.entries(o.attributes).map(([k, a]) => attrRow(k, a)).join("")}</div>`).join("");
  }
  if (globals.length) {
    html += "<h3>Environment · Mood · Style</h3>" + globals.map(([k, a]) => attrRow(k, a)).join("");
  }
  $("scene").innerHTML = html || '<div class="empty">Gesture to begin shaping the scene…</div>';
  setCompleteness(g.meta?.completeness ?? 0);
}

const attrRow = (k, a) =>
  `<div class="attr"><label>${k.replace(/_/g, " ")}</label><span>${a.value}</span>
   <div class="bar small"><div style="width:${a.confidence * 100}%"></div></div></div>`;

function setCompleteness(v) {
  const pct = Math.min(100, Math.max(0, (v ?? 0) * 100));
  $("completeness").textContent = `${pct | 0}%`;
  $("completeness-fill").style.width = `${pct}%`;
}

function prepend(id, html) {
  const el = $(id);
  const empty = el.querySelector(".empty");
  if (empty) empty.remove();
  el.insertAdjacentHTML("afterbegin", `<div class="row">${html}</div>`);
  while (el.children.length > 30) el.lastChild.remove();
}

function setStatus(text, cls) {
  $("status").textContent = text;
  $("status-dot").className = `dot ${cls || ""}`;
}

function showBanner(title, msgHtml, warn) {
  $("banner-title").textContent = title;
  $("banner-msg").innerHTML = msgHtml;
  const b = $("banner");
  b.className = warn ? "banner warn" : "banner";
  b.hidden = false;
}

function hideBanner() { $("banner").hidden = true; }

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
