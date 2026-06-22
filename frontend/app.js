// Frontend for the rating tables + time series. Manifest-driven: every rating system
// listed in data/systems.json becomes a tab, so future versions just drop in.

const state = { manifest: null, system: null, mode: "all", cache: {}, chart: null };

async function getJSON(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

function sysDef(id) { return state.manifest.systems.find((s) => s.id === id); }

async function init() {
  state.manifest = await getJSON("data/systems.json");
  const tabs = document.getElementById("tabs");
  state.manifest.systems.forEach((s) => {
    const b = document.createElement("button");
    b.textContent = s.label;
    b.dataset.id = s.id;
    b.onclick = () => selectSystem(s.id);
    tabs.appendChild(b);
  });
  document.querySelectorAll("input[name=mode]").forEach((r) => {
    r.onchange = () => { if (r.checked) { state.mode = r.value; render(); } };
  });
  selectSystem(state.manifest.systems[0].id);
}

async function selectSystem(id) {
  state.system = id;
  document.querySelectorAll("#tabs button")
    .forEach((b) => b.classList.toggle("active", b.dataset.id === id));
  const def = sysDef(id);
  if (!state.cache[id]) {
    const cur = await getJSON(`data/${id}_current.json`);
    const hist = def.hasHistory ? await getJSON(`data/${id}_history.json`) : null;
    state.cache[id] = { cur, hist };
  }
  render();
}

function activeRows() {
  const { cur } = state.cache[state.system];
  return state.mode === "wc" ? cur.filter((r) => r.wc2026) : cur;
}

function render() {
  const def = sysDef(state.system);
  document.getElementById("systemNote").textContent =
    def.kind === "fifa" ? "Reference benchmark — not used by the model" : "";
  renderTable(def);
  renderChart(def);
}

function renderTable(def) {
  const rows = activeRows();
  const cellsFor = def.kind === "elo"
    ? (r) => [
        { v: r.rank, num: true }, { v: team(r), num: false },
        { v: r.rating, num: true }, { v: r.games, num: true },
        { v: r.last_match, num: false },
      ]
    : (r) => [
        { v: r.rank, num: true }, { v: team(r), num: false },
        { v: r.points.toFixed(2), num: true }, { v: r.confederation, num: false },
      ];
  const headers = def.kind === "elo"
    ? ["#", "Team", "Rating", "Games", "Last match"]
    : ["#", "Team", "Points", "Confed"];

  const thead = "<tr>" + headers.map((h) => `<th>${h}</th>`).join("") + "</tr>";
  const body = rows.map((r) => {
    const tds = cellsFor(r)
      .map((c) => `<td class="${c.num ? "num" : ""}">${c.v}</td>`).join("");
    return `<tr class="${r.wc2026 ? "wc" : ""}">${tds}</tr>`;
  }).join("");
  document.getElementById("tableWrap").innerHTML =
    `<table><thead>${thead}</thead><tbody>${body}</tbody></table>`;
  document.getElementById("tableTitle").textContent =
    `Current ratings — ${def.label} (${rows.length})`;
}

function team(r) { return r.provisional ? `${r.team} *` : r.team; }

function colorFor(name) {
  let h = 0;
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return `hsl(${h}, 65%, 45%)`;
}

function renderChart(def) {
  const note = document.getElementById("chartNote");
  if (state.chart) { state.chart.destroy(); state.chart = null; }
  if (!def.hasHistory) { note.textContent = "No time series for this system."; return; }

  const hist = state.cache[state.system].hist;
  const teams = state.mode === "wc"
    ? state.manifest.wc2026.filter((t) => hist[t]) : Object.keys(hist);
  note.textContent = `${teams.length} teams`;

  const datasets = teams.map((t) => ({
    label: t,
    data: hist[t].map(([y, r]) => ({ x: y, y: r })),
    borderColor: colorFor(t), borderWidth: 1, pointRadius: 0, tension: 0.1,
  }));

  state.chart = new Chart(document.getElementById("chart"), {
    type: "line",
    data: { datasets },
    options: {
      animation: false, parsing: false, normalized: true, maintainAspectRatio: false,
      scales: { x: { type: "linear", ticks: { callback: (v) => v } },
                y: { title: { display: true, text: "Elo rating" } } },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { title: (i) => `${i[0].dataset.label} ${i[0].parsed.x}` } },
      },
      interaction: { mode: "nearest", intersect: false },
    },
  });
}

init().catch((e) => {
  document.body.insertAdjacentHTML("beforeend", `<p style="color:red">${e}</p>`);
});
