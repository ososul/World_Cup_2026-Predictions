// Typed contract for the JSON the Python pipeline emits into web/public/data.
// Shapes are fixed by prelim_elo/export_web.py and prelim_pred/export_predict.py —
// keep these in sync with those exporters (they are the source of truth for the data).

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
