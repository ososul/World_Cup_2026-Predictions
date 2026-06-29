"use client";

import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  type ChartOptions,
} from "chart.js";
import type { History } from "@/lib/types";
import type { Mode } from "@/components/ratings-view";

ChartJS.register(LinearScale, PointElement, LineElement, Tooltip);

// Stable per-team colour from a name hash (mirrors the original frontend's colorFor).
function colorFor(name: string): string {
  let h = 0;
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return `hsl(${h}, 65%, 45%)`;
}

const options: ChartOptions<"line"> = {
  animation: false,
  parsing: false,
  normalized: true,
  maintainAspectRatio: false,
  scales: {
    x: { type: "linear", ticks: { callback: (v) => `${v}` } },
    y: { title: { display: true, text: "Elo rating" } },
  },
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        title: (items) => `${items[0].dataset.label} ${items[0].parsed.x}`,
      },
    },
  },
  interaction: { mode: "nearest", intersect: false },
};

export function RatingChart({
  history,
  wc2026,
  mode,
}: {
  history: History;
  wc2026: string[];
  mode: Mode;
}) {
  const teams =
    mode === "wc" ? wc2026.filter((t) => history[t]) : Object.keys(history);
  const datasets = teams.map((t) => ({
    label: t,
    data: history[t].map(([y, r]) => ({ x: y, y: r })),
    borderColor: colorFor(t),
    borderWidth: 1,
    pointRadius: 0,
    tension: 0.1,
  }));

  return (
    <div>
      <div className="h-[72vh] rounded-md border p-1">
        <Line data={{ datasets }} options={options} />
      </div>
      <p className="mt-1 text-xs text-muted-foreground">{teams.length} teams</p>
    </div>
  );
}
