import type { Group, GroupsData } from "@/lib/types";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const qualRow: Record<string, string> = {
  direct: "bg-sky-50 dark:bg-sky-950/30",
  third: "bg-amber-50 dark:bg-amber-950/30",
};
const num = "text-right tabular-nums";

export function GroupsView({ data }: { data: GroupsData }) {
  const thirds = data.groups
    .map((g) => g.table.find((r) => r.qualified === "third"))
    .filter((r) => r !== undefined);
  return (
    <div>
      <div className="mb-4">
        <h1 className="text-sm font-medium">Group stage — final tables</h1>
        <p className="mt-1 text-xs text-muted-foreground">
          Top two qualify directly (blue). The eight best third-placed teams
          (amber) also advanced: {thirds.map((r) => r.team).join(", ")}.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data.groups.map((g) => (
          <GroupCard key={g.id} group={g} />
        ))}
      </div>
    </div>
  );
}

function GroupCard({ group }: { group: Group }) {
  return (
    <div className="rounded-md border">
      <div className="border-b px-3 py-2 text-sm font-medium">
        Group {group.id}
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className={num}>#</TableHead>
            <TableHead>Team</TableHead>
            <TableHead className={num}>W</TableHead>
            <TableHead className={num}>D</TableHead>
            <TableHead className={num}>L</TableHead>
            <TableHead className={num}>GF</TableHead>
            <TableHead className={num}>GA</TableHead>
            <TableHead className={num}>GD</TableHead>
            <TableHead className={num}>Pts</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {group.table.map((r) => (
            <TableRow
              key={r.team}
              className={r.qualified ? qualRow[r.qualified] : undefined}
            >
              <TableCell className={num}>{r.pos}</TableCell>
              <TableCell className="whitespace-normal">{r.team}</TableCell>
              <TableCell className={num}>{r.w}</TableCell>
              <TableCell className={num}>{r.d}</TableCell>
              <TableCell className={num}>{r.l}</TableCell>
              <TableCell className={num}>{r.gf}</TableCell>
              <TableCell className={num}>{r.ga}</TableCell>
              <TableCell className={num}>{r.gd > 0 ? `+${r.gd}` : r.gd}</TableCell>
              <TableCell className={`${num} font-medium`}>{r.pts}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <div className="border-t px-3 py-2">
        {group.matches.map((m) => (
          <div
            key={`${m.date}-${m.home}`}
            className="flex items-baseline justify-between gap-2 py-0.5 text-xs text-muted-foreground"
          >
            <span>
              {m.home} – {m.away}
            </span>
            <span className="tabular-nums">
              {m.homeScore}–{m.awayScore}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
