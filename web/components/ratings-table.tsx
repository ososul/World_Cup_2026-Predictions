import type { EloRow, FifaRow, SystemDef } from "@/lib/types";
import type { Mode } from "@/components/ratings-view";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const wcRow = "bg-sky-50 dark:bg-sky-950/30";
const num = "text-right tabular-nums";

export function RatingsTable({
  def,
  rows,
  mode,
}: {
  def: SystemDef;
  rows: EloRow[] | FifaRow[];
  mode: Mode;
}) {
  const filtered = mode === "wc" ? rows.filter((r) => r.wc2026) : rows;
  const isElo = def.kind === "elo";

  return (
    <div>
      <h2 className="mb-1 text-sm font-medium">
        Current ratings — {def.label} ({filtered.length})
      </h2>
      <div className="max-h-[72vh] overflow-auto rounded-md border">
        <Table>
          <TableHeader className="sticky top-0 z-10 bg-background">
            <TableRow>
              <TableHead className={num}>#</TableHead>
              <TableHead>Team</TableHead>
              {isElo ? (
                <>
                  <TableHead className={num}>Rating</TableHead>
                  <TableHead className={num}>Games</TableHead>
                  <TableHead>Last match</TableHead>
                </>
              ) : (
                <>
                  <TableHead className={num}>Points</TableHead>
                  <TableHead>Confed</TableHead>
                </>
              )}
            </TableRow>
          </TableHeader>
          <TableBody>
            {isElo
              ? (filtered as EloRow[]).map((r) => (
                  <TableRow key={r.team} className={r.wc2026 ? wcRow : undefined}>
                    <TableCell className={num}>{r.rank}</TableCell>
                    <TableCell>{r.provisional ? `${r.team} *` : r.team}</TableCell>
                    <TableCell className={num}>{r.rating}</TableCell>
                    <TableCell className={num}>{r.games}</TableCell>
                    <TableCell>{r.last_match}</TableCell>
                  </TableRow>
                ))
              : (filtered as FifaRow[]).map((r) => (
                  <TableRow key={r.team} className={r.wc2026 ? wcRow : undefined}>
                    <TableCell className={num}>{r.rank}</TableCell>
                    <TableCell>{r.team}</TableCell>
                    <TableCell className={num}>{r.points.toFixed(2)}</TableCell>
                    <TableCell>{r.confederation}</TableCell>
                  </TableRow>
                ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
