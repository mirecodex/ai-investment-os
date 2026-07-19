DASHBOARD_HTML = """<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Investment OS — Dashboard</title>
<style>
  :root {
    color-scheme: light;
    --surface: #fcfcfb;
    --card: #ffffff;
    --border: #e4e3df;
    --text-1: #0b0b0b;
    --text-2: #52514e;
    --series-1: #2a78d6;  /* confidence */
    --series-2: #008300;  /* hit rate */
    --good: #008300;
    --bad: #e34948;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      color-scheme: dark;
      --surface: #1a1a19;
      --card: #232322;
      --border: #3a3a38;
      --text-1: #ffffff;
      --text-2: #c3c2b7;
      --series-1: #3987e5;
      --series-2: #008300;
      --good: #4caf50;
      --bad: #e66767;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 1.5rem; background: var(--surface); color: var(--text-1);
    font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  h1 { font-size: 1.25rem; margin: 0 0 .25rem; }
  h2 { font-size: .95rem; margin: 0 0 .75rem; color: var(--text-2); font-weight: 600; }
  .disclaimer { color: var(--text-2); font-size: .8rem; margin-bottom: 1.25rem; }
  .grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
  .card {
    background: var(--card); border: 1px solid var(--border); border-radius: 8px;
    padding: 1rem; overflow-x: auto;
  }
  .tiles { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem; }
  .tile { flex: 1 1 140px; }
  .tile .value { font-size: 1.6rem; font-weight: 700; }
  .tile .label { color: var(--text-2); font-size: .8rem; }
  table { border-collapse: collapse; width: 100%; font-size: .85rem; }
  th, td { text-align: left; padding: .4rem .6rem; border-bottom: 1px solid var(--border); }
  th { color: var(--text-2); font-weight: 600; }
  .num { text-align: right; font-variant-numeric: tabular-nums; }
  .badge {
    display: inline-block; padding: 0 .5rem; border-radius: 999px; font-size: .75rem;
    font-weight: 700; border: 1px solid var(--border); color: var(--text-1);
  }
  .badge.BUY  { color: var(--good); border-color: var(--good); }
  .badge.SELL { color: var(--bad);  border-color: var(--bad); }
  .bar-row { display: flex; align-items: center; gap: .5rem; margin: .15rem 0; }
  .bar-label { width: 8.5rem; color: var(--text-2); font-size: .8rem; }
  .bar-track { flex: 1; }
  .bar {
    height: 8px; border-radius: 0 4px 4px 0; min-width: 2px;
    margin: 2px 0; /* 2px surface gap between paired bars */
  }
  .bar.conf { background: var(--series-1); }
  .bar.hit  { background: var(--series-2); }
  .bar-value { width: 3.5rem; font-size: .8rem; font-variant-numeric: tabular-nums; }
  .legend { display: flex; gap: 1rem; font-size: .8rem; color: var(--text-2); margin: .5rem 0; }
  .legend span::before {
    content: ""; display: inline-block; width: 10px; height: 10px; border-radius: 2px;
    margin-right: .35rem; vertical-align: baseline;
  }
  .legend .conf::before { background: var(--series-1); }
  .legend .hit::before  { background: var(--series-2); }
  .muted { color: var(--text-2); }
  select, button {
    font: inherit; padding: .35rem .6rem; border-radius: 6px;
    border: 1px solid var(--border); background: var(--card); color: var(--text-1);
  }
  button { cursor: pointer; }
  #analyze-result { margin-top: .75rem; font-size: .85rem; white-space: pre-wrap; }
</style>
</head>
<body>
<h1>AI Investment OS — IDX Edition</h1>
<div class="disclaimer" id="disclaimer">Riset &amp; edukasi, bukan nasihat investasi.</div>

<div class="tiles card" id="tiles"><span class="muted">Memuat market brief…</span></div>

<div class="grid">
  <div class="card">
    <h2>Kalibrasi confidence (horizon <span id="cal-horizon">20d</span>)</h2>
    <div id="calibration"><span class="muted">Memuat…</span></div>
  </div>
  <div class="card">
    <h2>Analisis on-demand</h2>
    <div>
      <select id="ticker-select"></select>
      <button id="analyze-btn">Analisis</button>
    </div>
    <div id="analyze-result" class="muted"></div>
  </div>
</div>

<div class="card" style="margin-top:1rem">
  <h2>Riwayat rekomendasi</h2>
  <div id="history"><span class="muted">Memuat…</span></div>
</div>

<script>
"use strict";
const fmtPct = (x) => (x * 100).toFixed(0) + "%";
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[c]));

async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(url + " -> HTTP " + res.status);
  return res.json();
}

async function loadBrief() {
  const brief = await getJSON("/brief");
  const flow = brief.net_foreign_flow_bn_idr;
  document.getElementById("disclaimer").textContent = brief.disclaimer;
  document.getElementById("tiles").innerHTML = [
    { label: "Sentimen pasar", value: esc(brief.sentiment) },
    { label: "IHSG hari ini", value: (brief.index_change_pct >= 0 ? "+" : "")
        + brief.index_change_pct.toFixed(2) + "%" },
    { label: "Arus asing (miliar IDR)", value: (flow >= 0 ? "+" : "") + flow.toFixed(0) },
    { label: "Tanggal", value: esc(brief.date) },
  ].map((tile) =>
    '<div class="tile"><div class="value">' + tile.value + '</div>'
    + '<div class="label">' + tile.label + "</div></div>"
  ).join("");
}

async function loadCalibration() {
  const cal = await getJSON("/calibration?horizon=20d");
  const root = document.getElementById("calibration");
  document.getElementById("cal-horizon").textContent = cal.horizon;
  if (!cal.directional_count) {
    root.innerHTML = '<span class="muted">Belum ada outcome terarah (BUY/SELL). '
      + "Outcome terekam otomatis setiap hari bursa.</span>";
    return;
  }
  const buckets = cal.buckets.map((b) => {
    const title = "conf " + b.low.toFixed(1) + "&ndash;" + b.high.toFixed(1) + ", n=" + b.count;
    return '<div class="bar-row" title="' + title + '">'
      + '<span class="bar-label">' + b.low.toFixed(1) + "&ndash;" + b.high.toFixed(1)
      + " (n=" + b.count + ")</span>"
      + '<span class="bar-track">'
      + '<div class="bar conf" style="width:' + (b.avg_confidence * 100) + '%"></div>'
      + '<div class="bar hit" style="width:' + (b.hit_rate * 100) + '%"></div>'
      + "</span>"
      + '<span class="bar-value">' + fmtPct(b.hit_rate) + "</span></div>";
  }).join("");
  root.innerHTML =
    "<div>Hit rate " + fmtPct(cal.overall_hit_rate) + " dari " + cal.directional_count
    + " outcome · ECE " + cal.ece.toFixed(3) + "</div>"
    + '<div class="legend"><span class="conf">rata-rata confidence</span>'
    + '<span class="hit">hit rate</span></div>' + buckets;
}

async function loadHistory() {
  const records = await getJSON("/recommendations?limit=50");
  const root = document.getElementById("history");
  if (!records.length) {
    root.innerHTML = '<span class="muted">Belum ada rekomendasi tersimpan.</span>';
    return;
  }
  const rows = records.map((r) =>
    "<tr><td>" + esc(r.created_at.slice(0, 16).replace("T", " ")) + "</td>"
    + "<td><b>" + esc(r.ticker) + "</b></td>"
    + '<td><span class="badge ' + esc(r.verdict) + '">' + esc(r.verdict) + "</span></td>"
    + '<td class="num">' + fmtPct(r.confidence) + " (" + esc(r.confidence_band) + ")</td>"
    + "<td>" + r.triggered_rule_ids.map(esc).join(", ") + "</td>"
    + "<td>" + esc(r.engine_version) + "</td></tr>"
  ).join("");
  root.innerHTML = "<table><thead><tr><th>Waktu (UTC)</th><th>Ticker</th><th>Keputusan</th>"
    + '<th class="num">Confidence</th><th>Rules</th><th>Engine</th></tr></thead>'
    + "<tbody>" + rows + "</tbody></table>";
}

async function loadTickers() {
  const tickers = await getJSON("/tickers");
  document.getElementById("ticker-select").innerHTML = tickers.map((t) =>
    '<option value="' + esc(t.ticker) + '">' + esc(t.ticker) + " — " + esc(t.name) + "</option>"
  ).join("");
}

async function analyze() {
  const button = document.getElementById("analyze-btn");
  const out = document.getElementById("analyze-result");
  const ticker = document.getElementById("ticker-select").value;
  button.disabled = true;
  out.textContent = "Menjalankan komite untuk " + ticker + "…";
  try {
    const res = await fetch("/analyze/" + encodeURIComponent(ticker), { method: "POST" });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const report = await res.json();
    const decision = report.decision;
    out.innerHTML = '<span class="badge ' + esc(decision.verdict) + '">'
      + esc(decision.verdict) + "</span> confidence " + fmtPct(decision.confidence)
      + " (" + esc(decision.confidence_band) + ")<br>" + esc(report.headline);
    loadHistory();
  } catch (err) {
    out.textContent = "Gagal: " + err.message;
  } finally {
    button.disabled = false;
  }
}

document.getElementById("analyze-btn").addEventListener("click", analyze);
for (const task of [loadBrief(), loadCalibration(), loadHistory(), loadTickers()]) {
  task.catch((err) => console.error(err));
}
</script>
</body>
</html>
"""
