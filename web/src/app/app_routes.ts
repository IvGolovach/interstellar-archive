export type AppRoute =
  | { kind: "mission" }
  | { kind: "parameters" }
  | { kind: "parameter-detail"; parameterId: string }
  | { kind: "failure-surface" }
  | { kind: "optimization"; candidateId?: string }
  | { kind: "capsule-lab" }
  | { kind: "mission-feasibility" }
  | { kind: "mission-runs"; runId?: string }
  | { kind: "cost-feasibility" }
  | { kind: "mission-probability"; couplingId?: string }
  | { kind: "uncertainty-interactions"; pairId?: string }
  | { kind: "evidence-campaign"; campaignId?: string }
  | { kind: "mission-dag-boundary"; moduleId?: string }
  | { kind: "external-review" }
  | { kind: "external-proof" }
  | { kind: "public-narrative" }
  | { kind: "roadmap-closure" }
  | { kind: "not-found"; raw: string };

export interface WorkspacePageProps {
  navigate: (route: AppRoute) => void;
  route: AppRoute;
}

interface NavItem {
  label: string;
  route: AppRoute;
}

export const DEFAULT_ROUTE: AppRoute = { kind: "mission" };

export const WORKSPACE_NAV_ITEMS: NavItem[] = [
  { label: "Mission", route: { kind: "mission" } },
  { label: "Parameters", route: { kind: "parameters" } },
  { label: "Failure Surface", route: { kind: "failure-surface" } },
  { label: "Optimization", route: { kind: "optimization" } },
  { label: "Capsule Lab", route: { kind: "capsule-lab" } },
  { label: "Feasibility", route: { kind: "mission-feasibility" } },
  { label: "Runs", route: { kind: "mission-runs" } },
  { label: "Cost", route: { kind: "cost-feasibility" } },
  { label: "Probability", route: { kind: "mission-probability" } },
  { label: "Uncertainty", route: { kind: "uncertainty-interactions" } },
  { label: "Evidence", route: { kind: "evidence-campaign" } },
  { label: "DAG Boundary", route: { kind: "mission-dag-boundary" } },
  { label: "External Review", route: { kind: "external-review" } },
  { label: "External Proof", route: { kind: "external-proof" } },
  { label: "Public Narrative", route: { kind: "public-narrative" } },
  { label: "V2 Closure", route: { kind: "roadmap-closure" } },
];

export function parseHashRoute(hash: string): AppRoute {
  const raw = hash.trim();
  if (raw === "" || raw === "#" || raw === "#/" || raw === "#mission" || raw === "#/mission") {
    return DEFAULT_ROUTE;
  }

  const normalized = raw.startsWith("#") ? raw.slice(1) : raw;
  const path = normalized.startsWith("/") ? normalized.slice(1) : normalized;
  const segments = path.split("/").filter(Boolean);
  if (segments.length === 0) {
    return DEFAULT_ROUTE;
  }

  const [first, second] = segments;
  if (first === "mission") {
    return { kind: "mission" };
  }
  if (first === "parameters") {
    if (!second) {
      return { kind: "parameters" };
    }
    return {
      kind: "parameter-detail",
      parameterId: decodeURIComponent(second),
    };
  }
  if (first === "failure-surface" || first === "failure") {
    return { kind: "failure-surface" };
  }
  if (first === "optimization" || first === "optimization-v2") {
    return { kind: "optimization", candidateId: second ? decodeURIComponent(second) : undefined };
  }
  if (first === "capsule-lab" || first === "capsule") {
    return { kind: "capsule-lab" };
  }
  if (first === "mission-feasibility" || first === "feasibility") {
    return { kind: "mission-feasibility" };
  }
  if (first === "mission-runs" || first === "runs") {
    return { kind: "mission-runs", runId: second ? decodeURIComponent(second) : undefined };
  }
  if (first === "cost-feasibility" || first === "cost" || first === "procurement") {
    return { kind: "cost-feasibility" };
  }
  if (first === "mission-probability" || first === "probability" || first === "coupling") {
    return { kind: "mission-probability", couplingId: second ? decodeURIComponent(second) : undefined };
  }
  if (first === "uncertainty-interactions" || first === "uncertainty" || first === "interactions") {
    return { kind: "uncertainty-interactions", pairId: second ? decodeURIComponent(second) : undefined };
  }
  if (first === "evidence-campaign" || first === "evidence-upgrade" || first === "evidence") {
    return { kind: "evidence-campaign", campaignId: second ? decodeURIComponent(second) : undefined };
  }
  if (first === "mission-dag-boundary" || first === "dag-boundary" || first === "dag-v2") {
    return { kind: "mission-dag-boundary", moduleId: second ? decodeURIComponent(second) : undefined };
  }
  if (first === "external-review" || first === "review-pack") {
    return { kind: "external-review" };
  }
  if (first === "external-proof" || first === "proof") {
    return { kind: "external-proof" };
  }
  if (first === "public-narrative" || first === "narrative") {
    return { kind: "public-narrative" };
  }
  if (first === "roadmap-closure" || first === "roadmap") {
    return { kind: "roadmap-closure" };
  }

  return { kind: "not-found", raw: path };
}

export function buildRouteHash(route: AppRoute): string {
  switch (route.kind) {
    case "mission":
      return "#/mission";
    case "parameters":
      return "#/parameters";
    case "parameter-detail":
      return `#/parameters/${encodeURIComponent(route.parameterId)}`;
    case "failure-surface":
      return "#/failure-surface";
    case "optimization":
      return route.candidateId ? `#/optimization/${encodeURIComponent(route.candidateId)}` : "#/optimization";
    case "capsule-lab":
      return "#/capsule-lab";
    case "mission-feasibility":
      return "#/mission-feasibility";
    case "mission-runs":
      return route.runId ? `#/mission-runs/${encodeURIComponent(route.runId)}` : "#/mission-runs";
    case "cost-feasibility":
      return "#/cost-feasibility";
    case "mission-probability":
      return route.couplingId
        ? `#/mission-probability/${encodeURIComponent(route.couplingId)}`
        : "#/mission-probability";
    case "uncertainty-interactions":
      return route.pairId
        ? `#/uncertainty-interactions/${encodeURIComponent(route.pairId)}`
        : "#/uncertainty-interactions";
    case "evidence-campaign":
      return route.campaignId
        ? `#/evidence-campaign/${encodeURIComponent(route.campaignId)}`
        : "#/evidence-campaign";
    case "mission-dag-boundary":
      return route.moduleId
        ? `#/mission-dag-boundary/${encodeURIComponent(route.moduleId)}`
        : "#/mission-dag-boundary";
    case "external-review":
      return "#/external-review";
    case "external-proof":
      return "#/external-proof";
    case "public-narrative":
      return "#/public-narrative";
    case "roadmap-closure":
      return "#/roadmap-closure";
    case "not-found":
      return `#/${route.raw}`;
    default:
      return "#/mission";
  }
}

export function routeTitle(route: AppRoute): string {
  switch (route.kind) {
    case "mission":
      return "Mission";
    case "parameters":
      return "Parameter Index";
    case "parameter-detail":
      return "Parameter Detail";
    case "failure-surface":
      return "Failure Surface";
    case "optimization":
      return "Optimization Lab";
    case "capsule-lab":
      return "Capsule Lab";
    case "mission-feasibility":
      return "Mission Feasibility";
    case "mission-runs":
      return "Mission Runs";
    case "cost-feasibility":
      return "Cost Feasibility";
    case "mission-probability":
      return "Mission Probability";
    case "uncertainty-interactions":
      return "Uncertainty Interactions";
    case "evidence-campaign":
      return "Evidence Campaign";
    case "mission-dag-boundary":
      return "DAG Boundary";
    case "external-review":
      return "External Review";
    case "external-proof":
      return "External Proof";
    case "public-narrative":
      return "Public Narrative";
    case "roadmap-closure":
      return "V2 Closure";
    case "not-found":
      return "Route Not Found";
    default:
      return "Mission";
  }
}

export function isActiveRoute(route: AppRoute, candidate: AppRoute["kind"]): boolean {
  if (candidate === "parameters" && route.kind === "parameter-detail") {
    return true;
  }
  return route.kind === candidate;
}
