// The single data-access seam. Today it reads the static JSON the Python pipeline
// writes into web/public/data. When a backend/API lands later, only these function
// bodies change (fs.readFile -> fetch the API) — UI components import from here and
// never read data directly, so the swap is local to this file.
import { promises as fs } from "node:fs";
import path from "node:path";

import type {
  SystemsManifest,
  EloRow,
  FifaRow,
  History,
  PredictConfig,
} from "./types";

const DATA_DIR = path.join(process.cwd(), "public", "data");

async function readJSON<T>(file: string): Promise<T> {
  const raw = await fs.readFile(path.join(DATA_DIR, file), "utf-8");
  return JSON.parse(raw) as T;
}

export function getSystems(): Promise<SystemsManifest> {
  return readJSON<SystemsManifest>("systems.json");
}

// Current ranked table for an Elo-kind system (e.g. "prelim_elo").
export function getRatings(systemId: string): Promise<EloRow[]> {
  return readJSON<EloRow[]>(`${systemId}_current.json`);
}

// Yearly rating history for a system that has one.
export function getHistory(systemId: string): Promise<History> {
  return readJSON<History>(`${systemId}_history.json`);
}

// The FIFA reference benchmark table.
export function getFifa(): Promise<FifaRow[]> {
  return readJSON<FifaRow[]>("fifa_current.json");
}

export function getPredictConfig(): Promise<PredictConfig> {
  return readJSON<PredictConfig>("predict.json");
}
