import { getGroups } from "@/lib/data";
import { GroupsView } from "@/components/groups-view";

// Server component: loads the finished group stage (tallies computed in Python,
// order = the official final standings) through the lib/data seam.
export default async function GroupsPage() {
  const data = await getGroups();
  return <GroupsView data={data} />;
}
