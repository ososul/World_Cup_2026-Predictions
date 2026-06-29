import { getSystems, getRatings, getHistory, getFifa } from "@/lib/data";
import { RatingsView, type SystemPayload } from "@/components/ratings-view";

// Server component: loads every rating system's data through the lib/data seam and
// hands it to the interactive client view. Manifest-driven — new systems exported by
// the Python pipeline appear automatically.
export default async function Home() {
  const manifest = await getSystems();

  const systems: SystemPayload[] = await Promise.all(
    manifest.systems.map(async (def): Promise<SystemPayload> => {
      if (def.kind === "fifa") {
        return { def, rows: await getFifa(), history: null };
      }
      const [rows, history] = await Promise.all([
        getRatings(def.id),
        def.hasHistory ? getHistory(def.id) : Promise.resolve(null),
      ]);
      return { def, rows, history };
    }),
  );

  return <RatingsView systems={systems} wc2026={manifest.wc2026} />;
}
