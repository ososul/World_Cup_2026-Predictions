import { getPredictConfig, getRatings } from "@/lib/data";
import { OddsPanel, type OddsTeam } from "@/components/odds-panel";

// Server component: loads the fitted model registry + the rating table through the
// lib/data seam, hands the interactive what-if compute to the client OddsPanel.
export default async function OddsPage() {
  const cfg = await getPredictConfig();
  const rows = await getRatings(cfg.ratingSystem);
  const teams: OddsTeam[] = rows.map((r) => ({
    team: r.team,
    rating: r.rating,
    wc: r.wc2026,
  }));
  return <OddsPanel cfg={cfg} teams={teams} />;
}
