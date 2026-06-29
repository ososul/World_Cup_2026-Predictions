"use client";

import { useState } from "react";
import type { EloRow, FifaRow, History, SystemDef } from "@/lib/types";
import { cn } from "@/lib/utils";
import { RatingsTable } from "@/components/ratings-table";
import { RatingChart } from "@/components/rating-chart";

export type SystemPayload = {
  def: SystemDef;
  rows: EloRow[] | FifaRow[];
  history: History | null;
};

export type Mode = "all" | "wc";

export function RatingsView({
  systems,
  wc2026,
}: {
  systems: SystemPayload[];
  wc2026: string[];
}) {
  const [systemId, setSystemId] = useState(systems[0]?.def.id ?? "");
  const [mode, setMode] = useState<Mode>("all");
  const active = systems.find((s) => s.def.id === systemId) ?? systems[0];
  if (!active) return null;

  return (
    <div className="space-y-4">
      {/* system tabs */}
      <div className="flex flex-wrap gap-1">
        {systems.map((s) => (
          <button
            key={s.def.id}
            type="button"
            onClick={() => setSystemId(s.def.id)}
            className={cn(
              "rounded-md border px-3 py-1.5 text-sm font-medium transition-colors",
              s.def.id === active.def.id
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-muted/40 text-muted-foreground hover:text-foreground",
            )}
          >
            {s.def.label}
          </button>
        ))}
      </div>

      {/* controls */}
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <span className="text-muted-foreground">Show:</span>
        <ModeToggle mode={mode} setMode={setMode} />
        {active.def.kind === "fifa" && (
          <span className="text-xs text-muted-foreground">
            Reference benchmark — not used by the model
          </span>
        )}
      </div>

      {/* table + chart */}
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="min-w-0">
          <RatingsTable def={active.def} rows={active.rows} mode={mode} />
        </section>
        <section className="min-w-0">
          <h2 className="mb-1 text-sm font-medium">
            Rating over time{" "}
            <span className="text-xs text-muted-foreground">
              (yearly samples)
            </span>
          </h2>
          {active.history ? (
            <RatingChart history={active.history} wc2026={wc2026} mode={mode} />
          ) : (
            <p className="text-xs text-muted-foreground">
              No time series for this system.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}

function ModeToggle({
  mode,
  setMode,
}: {
  mode: Mode;
  setMode: (m: Mode) => void;
}) {
  const opts: { v: Mode; label: string }[] = [
    { v: "all", label: "All teams" },
    { v: "wc", label: "WC 2026 only" },
  ];
  return (
    <div className="inline-flex overflow-hidden rounded-md border">
      {opts.map((o) => (
        <button
          key={o.v}
          type="button"
          onClick={() => setMode(o.v)}
          className={cn(
            "px-3 py-1 text-sm transition-colors",
            mode === o.v
              ? "bg-primary text-primary-foreground"
              : "bg-background text-muted-foreground hover:text-foreground",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
