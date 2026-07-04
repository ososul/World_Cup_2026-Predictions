import { getBracket } from "@/lib/data";
import { BracketView } from "@/components/bracket-view";

// Server component: loads the knockout projection (per-match quotes + exact-DP
// reach, all computed in Python) through the lib/data seam; the model selector,
// sorting and match detail are client-side in BracketView.
export default async function BracketPage() {
  const data = await getBracket();
  return <BracketView data={data} />;
}
