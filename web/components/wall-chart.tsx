"use client";

import { useMemo } from "react";
import type { BracketMatch } from "@/lib/types";

export const pct = (x: number) => (100 * x).toFixed(1) + "%";

// "W74" -> "Winner M74", "L101" -> "Loser M101"; group refs ("2A") pass through.
export function slotLabel(ref: string): string {
  const m = /^([WL])(\d+)$/.exec(ref);
  return m ? `${m[1] === "W" ? "Winner" : "Loser"} M${m[2]}` : ref;
}

// Mirrored wall chart: two halves of 8 R32 ties converging on a center Final,
// third place beneath it. Pure CSS grid — 17 columns (9 match + 8 connector),
// a header row + 16 uniform rows; a match at depth d (0 = R32 .. 3 = SF) and
// position i spans 2^(d+1) rows, so feeder centers land at 25% / 75% of each
// connector's span and the connectors are plain border shapes.

const HR = 1; // header row offset
const COLS =
  "8.5rem 1.25rem 8.5rem 1.25rem 8.5rem 1.25rem 8.5rem 1.25rem " + // left half
  "10rem " + // center (Final + third place)
  "1.25rem 8.5rem 1.25rem 8.5rem 1.25rem 8.5rem 1.25rem 8.5rem"; // right half
const ROWS = `auto repeat(16, 2.5rem)`;

const colOf = (side: "left" | "right", d: number) =>
  side === "left" ? 1 + 2 * d : 17 - 2 * d;
const connColOf = (side: "left" | "right", d: number) =>
  side === "left" ? 2 + 2 * d : 16 - 2 * d;
const rowOf = (d: number, i: number) =>
  `${i * 2 ** (d + 1) + 1 + HR} / span ${2 ** (d + 1)}`;

interface Tree {
  left: BracketMatch[][]; // columns [R32, R16, QF, SF], top-to-bottom
  right: BracketMatch[][];
  final: BracketMatch;
  third: BracketMatch | undefined;
}

// Derive the two halves by walking the winner-refs down from the Final —
// never by assuming match-number order (R32 numbering zig-zags the halves).
function buildTree(matches: BracketMatch[]): Tree | null {
  const by = new Map(matches.map((m) => [m.match, m]));
  const feeder = (ref: string) => {
    const r = /^W(\d+)$/.exec(ref);
    return r ? by.get(Number(r[1])) : undefined;
  };
  const final = matches.find((m) => m.round === "Final");
  const third = matches.find((m) => m.round === "3rd");
  const sfL = final && feeder(final.homeSlot);
  const sfR = final && feeder(final.awaySlot);
  if (!final || !sfL || !sfR) return null;
  const half = (sf: BracketMatch) => {
    const cols: BracketMatch[][] = [[], [], [], []];
    const walk = (m: BracketMatch, d: number) => {
      cols[d].push(m); // pre-order: home subtree above away subtree
      if (d === 0) return;
      const h = feeder(m.homeSlot);
      const a = feeder(m.awaySlot);
      if (h) walk(h, d - 1);
      if (a) walk(a, d - 1);
    };
    walk(sf, 3);
    return cols;
  };
  return { left: half(sfL), right: half(sfR), final, third };
}

export function WallChart({
  matches,
  modelId,
  selected,
  onSelect,
}: {
  matches: BracketMatch[];
  modelId: string;
  selected: number | null;
  onSelect: (no: number) => void;
}) {
  const tree = useMemo(() => buildTree(matches), [matches]);
  if (!tree) return null;
  const { final, third } = tree;
  const depthLabels = ["R32", "R16", "QF", "SF"];

  return (
    <div className="mx-[calc(50%-50vw)] overflow-x-auto">
      <div
        className="mx-auto grid w-max px-4"
        style={{ gridTemplateColumns: COLS, gridTemplateRows: ROWS }}
      >
        {/* column headers */}
        {(["left", "right"] as const).map((side) =>
          depthLabels.map((lb, d) => (
            <div
              key={`${side}-${lb}`}
              style={{ gridRow: 1, gridColumn: colOf(side, d) }}
              className="pb-2 text-center text-[11px] font-medium text-muted-foreground"
            >
              {lb}
            </div>
          )),
        )}
        <div
          style={{ gridRow: 1, gridColumn: 9 }}
          className="pb-2 text-center text-[11px] font-medium text-muted-foreground"
        >
          Final
        </div>

        {/* the two halves: match cards + connectors */}
        {(["left", "right"] as const).map((side) => {
          const cols = tree[side];
          return (
            <div key={side} className="contents">
              {cols.map((col, d) =>
                col.map((m, i) => (
                  <div
                    key={m.match}
                    style={{ gridRow: rowOf(d, i), gridColumn: colOf(side, d) }}
                    className="flex flex-col justify-center"
                  >
                    <MatchCard
                      m={m}
                      modelId={modelId}
                      selected={selected === m.match}
                      onSelect={onSelect}
                    />
                  </div>
                )),
              )}
              {/* pair connectors between depth d and d+1 */}
              {[0, 1, 2].map((d) =>
                Array.from({ length: cols[d].length / 2 }, (_, j) => (
                  <div
                    key={`c${d}-${j}`}
                    style={{
                      gridRow: `${j * 2 ** (d + 2) + 1 + HR} / span ${2 ** (d + 2)}`,
                      gridColumn: connColOf(side, d),
                    }}
                    className="relative"
                  >
                    {side === "left" ? (
                      <>
                        <div className="absolute top-1/4 bottom-1/4 left-0 right-1/2 border-y border-r" />
                        <div className="absolute top-1/2 left-1/2 right-0 border-t" />
                      </>
                    ) : (
                      <>
                        <div className="absolute top-1/4 bottom-1/4 right-0 left-1/2 border-y border-l" />
                        <div className="absolute top-1/2 right-1/2 left-0 border-t" />
                      </>
                    )}
                  </div>
                )),
              )}
              {/* straight SF -> Final line */}
              <div
                style={{
                  gridRow: `${1 + HR} / span 16`,
                  gridColumn: side === "left" ? 8 : 10,
                }}
                className="relative"
              >
                <div className="absolute top-1/2 inset-x-0 border-t" />
              </div>
            </div>
          );
        })}

        {/* center: Final on top, third place beneath */}
        <div
          style={{ gridRow: `${1 + HR} / span 16`, gridColumn: 9 }}
          className="flex flex-col justify-center gap-4"
        >
          <MatchCard
            m={final}
            modelId={modelId}
            selected={selected === final.match}
            onSelect={onSelect}
          />
          {third && (
            <div>
              <div className="mb-1 text-center text-[11px] font-medium text-muted-foreground">
                Third place
              </div>
              <MatchCard
                m={third}
                modelId={modelId}
                selected={selected === third.match}
                onSelect={onSelect}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function MatchCard({
  m,
  modelId,
  selected,
  onSelect,
}: {
  m: BracketMatch;
  modelId: string;
  selected: boolean;
  onSelect: (no: number) => void;
}) {
  const q = m.probs?.[modelId];
  return (
    <button
      type="button"
      onClick={() => onSelect(m.match)}
      className={
        "w-full rounded-md border bg-background px-2 py-1 text-left text-xs transition-colors hover:bg-muted/50 focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none" +
        (selected ? " border-ring bg-muted/50" : "")
      }
    >
      <div className="text-[10px] text-muted-foreground">
        M{m.match} &middot; {m.date.slice(5)}
      </div>
      <Side m={m} side="home" q={q} />
      <Side m={m} side="away" q={q} />
    </button>
  );
}

// One team row: name (or slot ref) + score once played, else advance % for the
// selected model. Winner in bold; names truncate with the full name on hover.
function Side({
  m,
  side,
  q,
}: {
  m: BracketMatch;
  side: "home" | "away";
  q: { advHome: number } | undefined;
}) {
  const team = side === "home" ? m.homeTeam : m.awayTeam;
  const label = team ?? slotLabel(side === "home" ? m.homeSlot : m.awaySlot);
  const won = team !== null && m.result?.winner === team;
  return (
    <div
      className={
        "flex items-baseline justify-between gap-2" +
        (won ? " font-medium" : "")
      }
    >
      <span
        className={"truncate" + (team ? "" : " text-muted-foreground")}
        title={label}
      >
        {label}
      </span>
      <span
        className={
          "shrink-0 tabular-nums" + (m.result ? "" : " text-muted-foreground")
        }
      >
        {m.result
          ? String(
              side === "home" ? m.result.homeScore : m.result.awayScore,
            ) + (won && m.result.pens ? " p" : "")
          : q
            ? pct(side === "home" ? q.advHome : 1 - q.advHome)
            : ""}
      </span>
    </div>
  );
}
