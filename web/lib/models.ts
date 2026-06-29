// 1X2 outcome models: rating difference dr -> [P(home), P(draw), P(away)].
//
// Faithful TypeScript port of prelim_pred/models.py (davidson_probs / ordlogit_probs /
// dixoncoles_probs). This duplication is a deliberate TEMPORARY bridge: it lets the odds
// panel compute arbitrary team pairings instantly in the browser with no backend. It is
// pinned to the Python implementation by __tests__/models.test.ts (which checks it against a
// Python-generated fixture), and it retires to an API endpoint once the backend lands.

export type Probs = [home: number, draw: number, away: number];
export type ModelFn = (dr: number, params: Record<string, number>) => Probs;

// Davidson draw extension on Elo's 400 scale (single free parameter nu).
function davidson(dr: number, p: Record<string, number>): Probs {
  const g = Math.pow(10, dr / 400);
  const sg = Math.pow(10, dr / 800);
  const den = g + 1 + p.nu * sg;
  return [g / den, (p.nu * sg) / den, 1 / den];
}

// Ordered logistic: latent gap m = b*dr, symmetric draw band +/- theta.
function ordlogit(dr: number, p: Record<string, number>): Probs {
  const s = (z: number) => 1 / (1 + Math.exp(-z));
  const m = p.b * dr;
  const pH = s(m - p.theta);
  const pA = s(-m - p.theta);
  return [pH, 1 - pH - pA, pA];
}

// Dixon-Coles: independent Poisson goals + low-score dependence (rho) on the four
// lowest cells (0-0, 1-0, 0-1, 1-1), renormalised over the truncated score grid.
function dixoncoles(dr: number, p: Record<string, number>): Probs {
  const MAX = 15;
  const x = dr / 400;
  const lamH = Math.exp(p.mu + p.beta * x);
  const lamA = Math.exp(p.mu - p.beta * x);

  const pmf = (lam: number): number[] => {
    const out = [Math.exp(-lam)];
    for (let k = 1; k <= MAX; k++) out.push((out[k - 1] * lam) / k);
    return out;
  };
  const tau = (i: number, j: number): number => {
    if (i === 0 && j === 0) return 1 - lamH * lamA * p.rho;
    if (i === 1 && j === 0) return 1 + lamA * p.rho;
    if (i === 0 && j === 1) return 1 + lamH * p.rho;
    if (i === 1 && j === 1) return 1 - p.rho;
    return 1;
  };

  const ph = pmf(lamH);
  const pa = pmf(lamA);
  let H = 0;
  let D = 0;
  let A = 0;
  for (let i = 0; i <= MAX; i++) {
    for (let j = 0; j <= MAX; j++) {
      let pij = ph[i] * pa[j];
      if (i <= 1 && j <= 1) {
        pij *= tau(i, j);
        if (pij < 0) pij = 0;
      }
      if (i > j) H += pij;
      else if (i === j) D += pij;
      else A += pij;
    }
  }
  const t = H + D + A;
  return [H / t, D / t, A / t];
}

export const MODELS: Record<string, ModelFn> = { davidson, ordlogit, dixoncoles };
