"use client";

import { Fragment, useMemo, useState, type CSSProperties } from "react";
import type {
  BracketData,
  BracketMatch,
  ModelDef,
  ReachRow,
  RoundId,
} from "@/lib/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { WallChart, pct, slotLabel } from "@/components/wall-chart";

const num = "text-right tabular-nums";
const selectCls =
  "rounded-md border bg-background px-2 py-1 text-sm focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none";

const ROUNDS: { id: RoundId; label: string }[] = [
  { id: "R32", label: "Round of 32" },
  { id: "R16", label: "Round of 16" },
  { id: "QF", label: "Quarter-finals" },
  { id: "SF", label: "Semi-finals" },
  { id: "3rd", label: "Third place" },
  { id: "Final", label: "Final" },
];

// Sequential heat tint for probability cells: one hue (sky-500), monotone in
// magnitude, anchored to the surface — the translucent tint darkens on light
// and lightens on dark automatically. Worst-case ink contrast (computed with
// the palette validator, not eyeballed): 11.3:1 light / 6.7:1 dark at p = 1.
const heat = (p: number): CSSProperties => ({
  backgroundColor: `rgba(14, 165, 233, ${(0.55 * p).toFixed(3)})`,
});

// Immutable Set toggle for visibility state.
function toggleSet<T>(prev: Set<T>, key: T): Set<T> {
  const next = new Set(prev);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  return next;
}

// A labelled row of on/off chips. A chip is "on" (shown) unless its key is in
// `hidden`; hidden chips read as struck-through and muted.
function Toggles<T extends string>({
  label,
  items,
  hidden,
  onToggle,
}: {
  label: string;
  items: { key: T; label: string }[];
  hidden: Set<T>;
  onToggle: (key: T) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1 text-xs">
      <span className="mr-1 text-muted-foreground">{label}</span>
      {items.map((it) => {
        const shown = !hidden.has(it.key);
        return (
          <button
            key={it.key}
            type="button"
            aria-pressed={shown}
            onClick={() => onToggle(it.key)}
            className={
              "rounded-md border px-2 py-0.5 transition-colors " +
              (shown
                ? "border-ring bg-muted/50 text-foreground"
                : "text-muted-foreground line-through hover:text-foreground")
            }
          >
            {it.label}
          </button>
        );
      })}
    </div>
  );
}

export function BracketView({ data }: { data: BracketData }) {
  // The exporter always emits the three models + "ensemble"; ensemble is the
  // headline view (and what the DP candidates use), so it is the default.
  const [modelId, setModelId] = useState("ensemble");
  const [selected, setSelected] = useState<number | null>(null);
  const [view, setView] = useState<"chart" | "tables">("chart");
  const [hiddenRounds, setHiddenRounds] = useState<Set<RoundId>>(new Set());

  const byRound = useMemo(() => {
    const m = new Map<RoundId, BracketMatch[]>();
    ROUNDS.forEach((r) => m.set(r.id, []));
    data.matches.forEach((x) => m.get(x.round)?.push(x)); // already in match order
    return m;
  }, [data.matches]);

  const selectedMatch =
    selected !== null
      ? data.matches.find((m) => m.match === selected)
      : undefined;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold">Knockout bracket — projection</h1>
          <p className="mt-1 max-w-2xl text-xs text-muted-foreground">
            Exact projection on static end-of-group ratings. Advance = win in
            90′, extra time (⅓-length Poisson) or penalties (50/50 in v1).
            Probabilities re-condition as results are entered. Click a match
            for detail.
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex rounded-md border p-0.5">
            {(["chart", "tables"] as const).map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setView(v)}
                className={
                  "rounded px-2 py-1 text-xs font-medium transition-colors " +
                  (view === v
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground")
                }
              >
                {v === "chart" ? "Wall chart" : "Tables"}
              </button>
            ))}
          </div>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-muted-foreground">Model</span>
            <select
              className={selectCls}
              value={modelId}
              onChange={(e) => setModelId(e.target.value)}
            >
              {data.models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <ReachMatrix reach={data.reach[modelId]} />

      {view === "chart" ? (
        <>
          <WallChart
            matches={data.matches}
            modelId={modelId}
            selected={selected}
            onSelect={(no) => setSelected((s) => (s === no ? null : no))}
          />
          {selectedMatch && (
            <div className="rounded-md border bg-muted/20 p-4">
              <MatchDetail
                m={selectedMatch}
                models={data.models}
                modelId={modelId}
              />
            </div>
          )}
        </>
      ) : (
        <>
          <Toggles
            label="Show rounds:"
            items={ROUNDS.map((r) => ({ key: r.id, label: r.id }))}
            hidden={hiddenRounds}
            onToggle={(id) => setHiddenRounds((prev) => toggleSet(prev, id))}
          />
          {ROUNDS.filter((r) => !hiddenRounds.has(r.id)).map((r) => (
            <RoundTable
              key={r.id}
              label={r.label}
              matches={byRound.get(r.id) ?? []}
              models={data.models}
              modelId={modelId}
              selected={selected}
              onSelect={(no) => setSelected((s) => (s === no ? null : no))}
            />
          ))}
        </>
      )}

      <p className="text-xs text-muted-foreground">
        {data.ratingSystem} ratings &middot; home advantage +{data.homeAdvantage}{" "}
        only when a host plays in its own country &middot; generated{" "}
        {data.generated}
      </p>
    </div>
  );
}

// --- reach matrix -----------------------------------------------------------

const REACH_COLS: { key: keyof ReachRow; label: string }[] = [
  { key: "r16", label: "R16" },
  { key: "qf", label: "QF" },
  { key: "sf", label: "SF" },
  { key: "final", label: "Final" },
  { key: "champion", label: "Champion" },
];

type SortKey = keyof ReachRow | "team";

function ReachMatrix({ reach }: { reach: Record<string, ReachRow> }) {
  const [sortKey, setSortKey] = useState<SortKey>("champion");
  const [hiddenCols, setHiddenCols] = useState<Set<keyof ReachRow>>(new Set());
  const cols = REACH_COLS.filter((c) => !hiddenCols.has(c.key));

  const rows = useMemo(() => {
    const list = Object.entries(reach);
    if (sortKey === "team") list.sort((a, b) => a[0].localeCompare(b[0]));
    else
      list.sort(
        (a, b) => b[1][sortKey] - a[1][sortKey] || a[0].localeCompare(b[0]),
      );
    return list;
  }, [reach, sortKey]);

  const arrow = (k: SortKey) =>
    sortKey === k ? (k === "team" ? " ▲" : " ▼") : "";

  return (
    <div>
      <h2 className="mb-1 text-sm font-medium">
        How far does each team go? — P(reach round)
      </h2>
      <div className="mb-2">
        <Toggles
          label="Show columns:"
          items={REACH_COLS.map((c) => ({ key: c.key, label: c.label }))}
          hidden={hiddenCols}
          onToggle={(key) => setHiddenCols((prev) => toggleSet(prev, key))}
        />
      </div>
      <div className="max-h-[60vh] overflow-auto rounded-md border">
        <Table>
          <TableHeader className="sticky top-0 z-10 bg-background">
            <TableRow>
              <TableHead>
                <button
                  type="button"
                  className="cursor-pointer"
                  onClick={() => setSortKey("team")}
                >
                  Team{arrow("team")}
                </button>
              </TableHead>
              {cols.map((c) => (
                <TableHead key={c.key} className={num}>
                  <button
                    type="button"
                    className="cursor-pointer"
                    onClick={() => setSortKey(c.key)}
                  >
                    {c.label}
                    {arrow(c.key)}
                  </button>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map(([team, r]) => (
              <TableRow key={team}>
                <TableCell>{team}</TableCell>
                {cols.map((c) => (
                  <TableCell key={c.key} className={num} style={heat(r[c.key])}>
                    {pct(r[c.key])}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        Click a column header to sort. Cell tint scales with probability.
      </p>
    </div>
  );
}

// --- round tables -----------------------------------------------------------

function TeamCell({ m, side }: { m: BracketMatch; side: "home" | "away" }) {
  const team = side === "home" ? m.homeTeam : m.awayTeam;
  if (!team)
    return (
      <span className="text-muted-foreground">
        {slotLabel(side === "home" ? m.homeSlot : m.awaySlot)}
      </span>
    );
  const won = m.result?.winner === team;
  return <span className={won ? "font-medium" : undefined}>{team}</span>;
}

function RoundTable({
  label,
  matches,
  models,
  modelId,
  selected,
  onSelect,
}: {
  label: string;
  matches: BracketMatch[];
  models: ModelDef[];
  modelId: string;
  selected: number | null;
  onSelect: (no: number) => void;
}) {
  return (
    <div className="rounded-md border">
      <div className="border-b px-3 py-2 text-sm font-medium">{label}</div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className={num}>M</TableHead>
            <TableHead>Date</TableHead>
            <TableHead>Home</TableHead>
            <TableHead>Away</TableHead>
            <TableHead className={num}>Home win</TableHead>
            <TableHead className={num}>Draw</TableHead>
            <TableHead className={num}>Away win</TableHead>
            <TableHead className={num}>Home advances</TableHead>
            <TableHead className={num}>Score</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {matches.map((m) => {
            const q = m.probs?.[modelId];
            const open = selected === m.match;
            return (
              <Fragment key={m.match}>
                <TableRow
                  tabIndex={0}
                  onClick={() => onSelect(m.match)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelect(m.match);
                    }
                  }}
                  className={"cursor-pointer" + (open ? " bg-muted/50" : "")}
                >
                  <TableCell className={num}>{m.match}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {m.date}
                  </TableCell>
                  <TableCell>
                    <TeamCell m={m} side="home" />
                  </TableCell>
                  <TableCell>
                    <TeamCell m={m} side="away" />
                  </TableCell>
                  <TableCell className={num}>
                    {q ? pct(q.p90[0]) : "—"}
                  </TableCell>
                  <TableCell className={num}>
                    {q ? pct(q.p90[1]) : "—"}
                  </TableCell>
                  <TableCell className={num}>
                    {q ? pct(q.p90[2]) : "—"}
                  </TableCell>
                  <TableCell className={num}>
                    {q ? pct(q.advHome) : "—"}
                  </TableCell>
                  <TableCell className={num}>
                    {m.result
                      ? `${m.result.homeScore}–${m.result.awayScore}` +
                        (m.result.pens ? " p" : "")
                      : ""}
                  </TableCell>
                </TableRow>
                {open && (
                  <TableRow className="hover:bg-transparent">
                    <TableCell
                      colSpan={9}
                      className="whitespace-normal bg-muted/20 p-4"
                    >
                      <MatchDetail m={m} models={models} modelId={modelId} />
                    </TableCell>
                  </TableRow>
                )}
              </Fragment>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

// --- match detail -----------------------------------------------------------

function MatchDetail({
  m,
  models,
  modelId,
}: {
  m: BracketMatch;
  models: ModelDef[];
  modelId: string;
}) {
  const q = m.probs?.[modelId];
  const modelLabel = models.find((x) => x.id === modelId)?.label ?? modelId;
  // Advance waterfall recombines exported legs: win in 90′ = p90[w]; win in
  // ET = p90[draw]·et[w]; win on pens = p90[draw]·et[draw]·pensWin. The total
  // column shows the exported advHome directly so rounding cannot drift.
  const legs = q
    ? {
        home: [
          q.p90[0],
          q.p90[1] * q.et[0],
          q.p90[1] * q.et[1] * q.pensWin,
          q.advHome,
        ],
        away: [
          q.p90[2],
          q.p90[1] * q.et[2],
          q.p90[1] * q.et[1] * (1 - q.pensWin),
          1 - q.advHome,
        ],
      }
    : null;

  return (
    <div className="space-y-3 text-sm">
      <div className="text-xs text-muted-foreground">
        M{m.match} &middot; {m.round} &middot; {m.date} &middot;{" "}
        {m.venueCountry} &middot; {slotLabel(m.homeSlot)} vs{" "}
        {slotLabel(m.awaySlot)}
      </div>

      {m.result && (
        <p className="font-medium">
          {m.homeTeam} {m.result.homeScore}–{m.result.awayScore} {m.awayTeam}
          {m.result.pens && ` — ${m.result.winner} advance on penalties`}
        </p>
      )}

      {m.probs && (
        <div>
          <h3 className="mb-1 text-xs font-medium">All models</h3>
          <table className="border-collapse text-sm">
            <thead>
              <tr>
                <th className="px-3 py-1 text-left font-medium text-muted-foreground">
                  Model
                </th>
                <th className="px-3 py-1 text-right font-medium">
                  {m.homeTeam} win
                </th>
                <th className="px-3 py-1 text-right font-medium">Draw</th>
                <th className="px-3 py-1 text-right font-medium">
                  {m.awayTeam} win
                </th>
                <th className="px-3 py-1 text-right font-medium">
                  {m.homeTeam} adv
                </th>
                <th className="px-3 py-1 text-right font-medium">
                  {m.awayTeam} adv
                </th>
              </tr>
            </thead>
            <tbody>
              {models.map((md) => {
                const p = m.probs?.[md.id];
                if (!p) return null;
                return (
                  <tr
                    key={md.id}
                    className={
                      "border-t" + (md.id === modelId ? " bg-muted/40" : "")
                    }
                  >
                    <td className="px-3 py-1 text-muted-foreground">
                      {md.label}
                    </td>
                    <td className="px-3 py-1 text-right tabular-nums">
                      {pct(p.p90[0])}
                    </td>
                    <td className="px-3 py-1 text-right tabular-nums">
                      {pct(p.p90[1])}
                    </td>
                    <td className="px-3 py-1 text-right tabular-nums">
                      {pct(p.p90[2])}
                    </td>
                    <td className="px-3 py-1 text-right tabular-nums">
                      {pct(p.advHome)}
                    </td>
                    <td className="px-3 py-1 text-right tabular-nums">
                      {pct(1 - p.advHome)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {legs && (
        <div>
          <h3 className="mb-1 text-xs font-medium">
            Advance waterfall — {modelLabel}
          </h3>
          <table className="border-collapse text-sm">
            <thead>
              <tr>
                <th className="px-3 py-1 text-left font-medium text-muted-foreground"></th>
                <th className="px-3 py-1 text-right font-medium">In 90′</th>
                <th className="px-3 py-1 text-right font-medium">
                  In extra time
                </th>
                <th className="px-3 py-1 text-right font-medium">
                  On penalties
                </th>
                <th className="px-3 py-1 text-right font-medium">Advance</th>
              </tr>
            </thead>
            <tbody>
              {(["home", "away"] as const).map((side) => (
                <tr key={side} className="border-t">
                  <td className="px-3 py-1 text-muted-foreground">
                    {side === "home" ? m.homeTeam : m.awayTeam}
                  </td>
                  {legs[side].map((v, i) => (
                    <td
                      key={i}
                      className={
                        "px-3 py-1 text-right tabular-nums" +
                        (i === 3 ? " font-medium" : "")
                      }
                    >
                      {pct(v)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {m.scorelines && (
        <p className="text-xs text-muted-foreground">
          Most likely 90′ scores (Dixon-Coles):{" "}
          {m.scorelines.map(([s, p]) => `${s} ${pct(p)}`).join(" · ")}
        </p>
      )}

      {m.candidates && (
        <div>
          <h3 className="mb-1 text-xs font-medium">
            Who arrives here — ensemble probabilities (independent of the model
            selector)
          </h3>
          <div className="flex flex-wrap gap-x-12 gap-y-3">
            {(["home", "away"] as const).map((side) => {
              const team = side === "home" ? m.homeTeam : m.awayTeam;
              if (team) return null; // known side: nothing to list
              return (
                <div key={side}>
                  <div className="mb-0.5 text-xs text-muted-foreground">
                    {slotLabel(side === "home" ? m.homeSlot : m.awaySlot)}
                  </div>
                  {m.candidates?.[side].map((c) => (
                    <div
                      key={c.team}
                      className="flex justify-between gap-6"
                    >
                      <span>{c.team}</span>
                      <span className="tabular-nums">{pct(c.p)}</span>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
