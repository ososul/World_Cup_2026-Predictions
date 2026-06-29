"use client";

import { useMemo, useState } from "react";
import type { PredictConfig } from "@/lib/types";
import { MODELS } from "@/lib/models";

export type OddsTeam = { team: string; rating: number; wc: boolean };
type Venue = "N" | "A" | "B";

const pct = (x: number) => (100 * x).toFixed(1) + "%";
const odd = (x: number) => (x > 0 ? (1 / x).toFixed(2) : "—");

const selectCls =
  "rounded-md border bg-background px-2 py-1 text-sm focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none";

export function OddsPanel({
  cfg,
  teams,
}: {
  cfg: PredictConfig;
  teams: OddsTeam[];
}) {
  const ratingMap = useMemo(() => {
    const m = new Map<string, OddsTeam>();
    teams.forEach((t) => m.set(t.team, t));
    return m;
  }, [teams]);

  const [modelId, setModelId] = useState(cfg.models[0]?.id ?? "");
  const [wcOnly, setWcOnly] = useState(false);
  const [venue, setVenue] = useState<Venue>("N");

  const teamList = useMemo(
    () =>
      teams
        .filter((t) => !wcOnly || t.wc)
        .map((t) => t.team)
        .sort(),
    [teams, wcOnly],
  );

  const [teamA, setTeamA] = useState(teamList[0] ?? "");
  const [teamB, setTeamB] = useState(teamList[1] ?? teamList[0] ?? "");

  // Keep selections valid when the WC-only filter changes the available teams.
  function changeWcOnly(checked: boolean) {
    setWcOnly(checked);
    const list = teams
      .filter((t) => !checked || t.wc)
      .map((t) => t.team)
      .sort();
    setTeamA((a) => (list.includes(a) ? a : (list[0] ?? "")));
    setTeamB((b) => (list.includes(b) ? b : (list[1] ?? list[0] ?? "")));
  }

  function swap() {
    setTeamA(teamB);
    setTeamB(teamA);
  }

  const a = ratingMap.get(teamA);
  const b = ratingMap.get(teamB);
  const model = cfg.models.find((m) => m.id === modelId);
  const H = cfg.homeAdvantage;

  let result: {
    dr: number;
    ra: number;
    rb: number;
    pA: number;
    pD: number;
    pB: number;
  } | null = null;
  if (a && b && model) {
    const dr =
      a.rating - b.rating + (venue === "A" ? H : venue === "B" ? -H : 0);
    const [pA, pD, pB] = MODELS[model.id](dr, model.params);
    result = { dr, ra: a.rating, rb: b.rating, pA, pD, pB };
  }

  const venueNote =
    venue === "N"
      ? "neutral venue"
      : venue === "A"
        ? `${teamA} at home (+${H})`
        : `${teamB} at home (+${H})`;

  return (
    <div className="space-y-3">
      <h1 className="text-lg font-semibold">Match odds</h1>

      <div className="flex flex-wrap items-end gap-3 rounded-lg border bg-muted/20 p-3 text-sm">
        <Field label="Model">
          <select
            className={selectCls}
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
          >
            {cfg.models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Team A">
          <select
            className={selectCls}
            value={teamA}
            onChange={(e) => setTeamA(e.target.value)}
          >
            {teamList.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Team B">
          <select
            className={selectCls}
            value={teamB}
            onChange={(e) => setTeamB(e.target.value)}
          >
            {teamList.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Venue">
          <select
            className={selectCls}
            value={venue}
            onChange={(e) => setVenue(e.target.value as Venue)}
          >
            <option value="N">Neutral</option>
            <option value="A">Team A home</option>
            <option value="B">Team B home</option>
          </select>
        </Field>

        <label className="flex items-center gap-1.5">
          <input
            type="checkbox"
            checked={wcOnly}
            onChange={(e) => changeWcOnly(e.target.checked)}
          />
          WC 2026 teams only
        </label>

        <button
          type="button"
          onClick={swap}
          className="rounded-md border bg-background px-3 py-1 text-sm hover:bg-muted"
        >
          Swap A/B
        </button>
      </div>

      {result && (
        <div>
          <table className="border-collapse text-sm">
            <tbody>
              <tr>
                <th className="px-3 py-1 text-left font-medium text-muted-foreground"></th>
                <th className="px-3 py-1 text-right font-medium">{teamA} win</th>
                <th className="px-3 py-1 text-right font-medium">Draw</th>
                <th className="px-3 py-1 text-right font-medium">{teamB} win</th>
              </tr>
              <tr className="border-t">
                <td className="px-3 py-1 text-muted-foreground">Probability</td>
                <td className="px-3 py-1 text-right tabular-nums">
                  {pct(result.pA)}
                </td>
                <td className="px-3 py-1 text-right tabular-nums">
                  {pct(result.pD)}
                </td>
                <td className="px-3 py-1 text-right tabular-nums">
                  {pct(result.pB)}
                </td>
              </tr>
              <tr className="border-t">
                <td className="px-3 py-1 text-muted-foreground">Fair odds</td>
                <td className="px-3 py-1 text-right tabular-nums">
                  {odd(result.pA)}
                </td>
                <td className="px-3 py-1 text-right tabular-nums">
                  {odd(result.pD)}
                </td>
                <td className="px-3 py-1 text-right tabular-nums">
                  {odd(result.pB)}
                </td>
              </tr>
            </tbody>
          </table>
          <p className="mt-1 text-xs text-muted-foreground">
            {teamA} {result.ra} vs {teamB} {result.rb} &middot; {venueNote}{" "}
            &middot; dr = {result.dr >= 0 ? "+" : ""}
            {result.dr}
          </p>
        </div>
      )}
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-muted-foreground">{label}</span>
      {children}
    </label>
  );
}
