import type { WorkspacePageProps } from "../app/app_routes";
import { loadParameterDrilldownDataset } from "../lib/parameter_drilldown_loader";
import { EvidenceCampaignPanel } from "../ui/evidence_campaign/EvidenceCampaignPanel";

export default function EvidenceCampaignRoute({ navigate, route }: WorkspacePageProps): JSX.Element {
  const dataset = loadParameterDrilldownDataset({ strict: true });
  const campaignId = route.kind === "evidence-campaign" ? route.campaignId : undefined;

  return (
    <EvidenceCampaignPanel
      artifact={dataset.evidenceUpgradeCampaign}
      selectedCampaignId={campaignId}
      onSelectCampaign={(nextCampaignId) => navigate({ kind: "evidence-campaign", campaignId: nextCampaignId })}
    />
  );
}
