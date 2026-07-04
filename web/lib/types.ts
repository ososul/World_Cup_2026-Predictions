// Typed contract for the JSON the Python pipeline emits into web/public/data.
// Shapes are fixed by prelim_elo/export_web.py, prelim_pred/export_predict.py and
// prelim_pred/export_tournament.py — keep these in sync with those exporters
// (they are the source of truth for the data).

export type SystemKind = "elo" | "fifa";

export interface SystemDef {
  id: string;
  label: string;
  kind: SystemKind;
  hasHistory: boolean;
}

export interface SystemsManifest {
  wc2026: string[];
  systems: SystemDef[];
}

// prelim_elo_current.json — one row per team, ranked by rating.
export interface EloRow {
  rank: number;
  team: string;
  rating: number;
  games: number;
  provisional: boolean;
  last_match: string;
  wc2026: boolean;
}

// fifa_current.json — reference benchmark only (never a model input).
export interface FifaRow {
  rank: number;
  team: string;
  points: number;
  confederation: string;
  wc2026: boolean;
}

// prelim_elo_history.json — per-team yearly samples as [year, rating] pairs.
export type History = Record<string, [year: number, rating: number][]>;

// One outcome model's fitted free parameters (davidson: { nu }, ordlogit: { b, theta }, ...).
export interface ModelDef {
  id: string;
  label: string;
  params: Record<string, number>;
}

// predict.json — registry the match-odds panel reads.
export interface PredictConfig {
  eloScale: number;
  homeAdvantage: number;
  ratingSystem: string;
  models: ModelDef[];
}

// groups.json — finished group stage: computed tallies shown in the entered
// (official) final order, plus each group's six played results.
export interface GroupRow {
  pos: number;
  team: string;
  w: number;
  d: number;
  l: number;
  gf: number;
  ga: number;
  gd: number;
  pts: number;
  qualified: "direct" | "third" | null;
}

export interface GroupMatch {
  date: string;
  home: string;
  away: string;
  homeScore: number;
  awayScore: number;
}

export interface Group {
  id: string;
  table: GroupRow[];
  matches: GroupMatch[];
}

export interface GroupsData {
  generated: string;
  groups: Group[];
}

// bracket.json — the knockout bracket: resolved state, per-match model quotes,
// and the exact-DP projection (reach matrix + slot candidates).
export type RoundId = "R32" | "R16" | "QF" | "SF" | "3rd" | "Final";

// One model's quote for a known pairing. p90/et are [homeWin, draw, awayWin];
// et is the extra-time mini-match conditioned on a 90' draw; advHome is the
// full three-leg advance probability (away = 1 - advHome exactly).
export interface ModelQuote {
  p90: [number, number, number];
  et: [number, number, number];
  pensWin: number;
  advHome: number;
}

export interface MatchResult {
  homeScore: number;
  awayScore: number;
  winner: string;
  pens: boolean;
}

// One entry of a slot's arrival distribution (ensemble DP, sorted by p desc).
export interface Candidate {
  team: string;
  p: number;
}

export interface BracketMatch {
  match: number;
  round: RoundId;
  date: string;
  venueCountry: string;
  homeSlot: string; // "2A" (group ref), "W74" (winner-ref) or "L101" (loser-ref)
  awaySlot: string;
  homeTeam: string | null;
  awayTeam: string | null;
  status: "scheduled" | "played";
  result: MatchResult | null;
  probs: Record<string, ModelQuote> | null; // by model id incl. "ensemble"; set iff both teams known
  scorelines: [score: string, p: number][] | null; // top-3 Dixon-Coles 90' cells
  candidates: { home: Candidate[]; away: Candidate[] } | null; // set iff a slot is unresolved
}

// P(reach each round) for one team; champion = P(win the Final).
export interface ReachRow {
  r16: number;
  qf: number;
  sf: number;
  final: number;
  champion: number;
}

export interface BracketData {
  ratingSystem: string;
  homeAdvantage: number;
  generated: string;
  models: ModelDef[]; // davidson/ordlogit/dixoncoles + "ensemble"
  resolution: { muPois: number; betaPois: number; pens: number };
  matches: BracketMatch[];
  reach: Record<string, Record<string, ReachRow>>; // model id -> team -> reach
}
