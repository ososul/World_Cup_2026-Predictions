// Match-odds panel: pick two teams + venue + model and compute W/D/L from the
// Preliminary Elo ratings, entirely in the browser. The model math mirrors
// prelim_pred/models.py exactly. Add a model by appending an entry to data/predict.json
// and a matching function to MODELS, keyed by the id.

const PRED = { cfg: null, ratings: {} };

const MODELS = {
  // Davidson draw extension on Elo's 400 scale. Returns [P(A win), P(draw), P(B win)].
  davidson(dr, p) {
    const g = Math.pow(10, dr / 400), sg = Math.pow(10, dr / 800);
    const den = g + 1 + p.nu * sg;
    return [g / den, (p.nu * sg) / den, 1 / den];
  },
  // Ordered logistic: latent gap m = b*dr, symmetric draw band +/- theta.
  ordlogit(dr, p) {
    const s = (z) => 1 / (1 + Math.exp(-z));
    const m = p.b * dr;
    const pH = s(m - p.theta), pA = s(-m - p.theta);
    return [pH, 1 - pH - pA, pA];
  },
  // Dixon-Coles goals: Poisson + low-score dependence on the four lowest cells
  // (mirrors models.dixoncoles_probs; rho = 0 would reduce to plain Poisson).
  dixoncoles(dr, p) {
    const MAX = 15, x = dr / 400;
    const lamH = Math.exp(p.mu + p.beta * x), lamA = Math.exp(p.mu - p.beta * x);
    const pmf = (lam) => {
      const out = [Math.exp(-lam)];
      for (let k = 1; k <= MAX; k++) out.push(out[k - 1] * lam / k);
      return out;
    };
    const tau = (i, j) => {
      if (i === 0 && j === 0) return 1 - lamH * lamA * p.rho;
      if (i === 1 && j === 0) return 1 + lamA * p.rho;
      if (i === 0 && j === 1) return 1 + lamH * p.rho;
      if (i === 1 && j === 1) return 1 - p.rho;
      return 1;
    };
    const ph = pmf(lamH), pa = pmf(lamA);
    let H = 0, D = 0, A = 0;
    for (let i = 0; i <= MAX; i++) for (let j = 0; j <= MAX; j++) {
      let pij = ph[i] * pa[j];
      if (i <= 1 && j <= 1) { pij *= tau(i, j); if (pij < 0) pij = 0; }
      if (i > j) H += pij; else if (i === j) D += pij; else A += pij;
    }
    const t = H + D + A;
    return [H / t, D / t, A / t];
  },
};

async function pget(path) {
  const r = await fetch(`${path}?t=${Date.now()}`); // cache-bust so a page reload shows re-exported data
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

async function loadPrediction() {
  PRED.cfg = await pget("data/predict.json");
  const rows = await pget(`data/${PRED.cfg.ratingSystem}_current.json`);
  PRED.ratings = {};
  rows.forEach((r) => (PRED.ratings[r.team] = { rating: r.rating, wc: r.wc2026 }));
  fillModels();
  fillTeams();
  computeOdds();
}

function fillModels() {
  document.getElementById("modelSel").innerHTML = PRED.cfg.models
    .map((m) => `<option value="${m.id}">${m.label}</option>`).join("");
}

function teamList() {
  const wcOnly = document.getElementById("wcOnly").checked;
  return Object.keys(PRED.ratings).filter((t) => !wcOnly || PRED.ratings[t].wc).sort();
}

function fillTeams() {
  const teams = teamList();
  ["teamA", "teamB"].forEach((id, i) => {
    const sel = document.getElementById(id);
    const prev = sel.value;
    sel.innerHTML = teams.map((t) => `<option>${t}</option>`).join("");
    if (teams.includes(prev)) sel.value = prev;
    else sel.selectedIndex = Math.min(i, teams.length - 1); // default A = 1st, B = 2nd
  });
  const A = document.getElementById("teamA"), B = document.getElementById("teamB");
  if (A.value === B.value && teams.length > 1) B.selectedIndex = 1;
}

function modelParams(id) {
  return PRED.cfg.models.find((m) => m.id === id).params;
}

function computeOdds() {
  const out = document.getElementById("oddsOut");
  const a = document.getElementById("teamA").value;
  const b = document.getElementById("teamB").value;
  if (!a || !b) { out.textContent = ""; return; }
  const ra = PRED.ratings[a].rating, rb = PRED.ratings[b].rating;
  const venue = document.getElementById("venue").value;
  const H = PRED.cfg.homeAdvantage;
  const dr = ra - rb + (venue === "A" ? H : venue === "B" ? -H : 0);
  const id = document.getElementById("modelSel").value;
  const [pA, pD, pB] = MODELS[id](dr, modelParams(id));
  out.innerHTML = renderOdds(a, b, ra, rb, dr, venue, pA, pD, pB);
}

const pct = (x) => (100 * x).toFixed(1) + "%";
const odd = (x) => (x > 0 ? (1 / x).toFixed(2) : "—");

function renderOdds(a, b, ra, rb, dr, venue, pA, pD, pB) {
  const H = PRED.cfg.homeAdvantage;
  const venueNote = venue === "N" ? "neutral venue"
    : venue === "A" ? `${a} at home (+${H})` : `${b} at home (+${H})`;
  return `
    <table class="oddstable">
      <tr><th></th><th>${a} win</th><th>Draw</th><th>${b} win</th></tr>
      <tr><td>Probability</td><td class="num">${pct(pA)}</td><td class="num">${pct(pD)}</td><td class="num">${pct(pB)}</td></tr>
      <tr><td>Fair odds</td><td class="num">${odd(pA)}</td><td class="num">${odd(pD)}</td><td class="num">${odd(pB)}</td></tr>
    </table>
    <p class="note">${a} ${ra} vs ${b} ${rb} &middot; ${venueNote} &middot; dr = ${dr >= 0 ? "+" : ""}${dr}</p>`;
}

function initPredict() {
  document.getElementById("swapBtn").onclick = () => {
    const A = document.getElementById("teamA"), B = document.getElementById("teamB");
    const t = A.value; A.value = B.value; B.value = t;
    computeOdds();
  };
  ["modelSel", "teamA", "teamB", "venue"].forEach((id) =>
    document.getElementById(id).addEventListener("change", computeOdds));
  document.getElementById("wcOnly").addEventListener("change", () => { fillTeams(); computeOdds(); });
  loadPrediction().catch((e) =>
    (document.getElementById("oddsOut").innerHTML = `<p style="color:red">${e}</p>`));
}

initPredict();
