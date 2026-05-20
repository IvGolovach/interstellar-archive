import { lazy, Suspense } from "react";

import {
  buildRouteHash,
  isActiveRoute,
  routeTitle,
  type AppRoute,
  type WorkspacePageProps,
  WORKSPACE_NAV_ITEMS,
} from "./app/app_routes";
import { useHashRoute } from "./app/useHashRoute";

const MissionRoute = lazy(() => import("./pages/MissionRoute"));
const ParameterIndexRoute = lazy(() => import("./pages/ParameterIndexRoute"));
const ParameterDetailRoute = lazy(() => import("./pages/ParameterDetailRoute"));
const FailureSurfaceRoute = lazy(() => import("./pages/FailureSurfaceRoute"));
const OptimizationLabRoute = lazy(() => import("./pages/OptimizationLabRoute"));
const CapsuleLabRoute = lazy(() => import("./pages/CapsuleLabRoute"));
const MissionFeasibilityRoute = lazy(() => import("./pages/MissionFeasibilityRoute"));
const UserMissionRunRoute = lazy(() => import("./pages/UserMissionRunRoute"));
const CostFeasibilityRoute = lazy(() => import("./pages/CostFeasibilityRoute"));
const MissionProbabilityCouplingRoute = lazy(() => import("./pages/MissionProbabilityCouplingRoute"));
const UncertaintyInteractionsRoute = lazy(() => import("./pages/UncertaintyInteractionsRoute"));
const EvidenceCampaignRoute = lazy(() => import("./pages/EvidenceCampaignRoute"));
const MissionDagBoundaryRoute = lazy(() => import("./pages/MissionDagBoundaryRoute"));
const ExternalReviewRoute = lazy(() => import("./pages/ExternalReviewRoute"));
const ExternalProofRoute = lazy(() => import("./pages/ExternalProofRoute"));
const PublicNarrativeRoute = lazy(() => import("./pages/PublicNarrativeRoute"));
const RoadmapClosureRoute = lazy(() => import("./pages/RoadmapClosureRoute"));

function LoadingPanel({ label }: { label: string }): JSX.Element {
  return (
    <section className="panel route-loading" aria-live="polite">
      <p className="eyebrow">Loading</p>
      <p>{label} is loading.</p>
    </section>
  );
}

function NotFoundRoute({ navigate, route }: WorkspacePageProps): JSX.Element {
  return (
    <section className="panel">
      <h2>Route Not Found</h2>
      <p className="help-text mono-cell">Unknown hash route: {route.kind === "not-found" ? route.raw : "unknown"}</p>
      <button type="button" className="ghost-button" onClick={() => navigate({ kind: "mission" })}>
        Return to Mission
      </button>
    </section>
  );
}

function renderRoute(route: AppRoute, navigate: (next: AppRoute) => void): JSX.Element {
  const props: WorkspacePageProps = { navigate, route };
  switch (route.kind) {
    case "mission":
      return <MissionRoute {...props} />;
    case "parameters":
      return <ParameterIndexRoute {...props} />;
    case "parameter-detail":
      return <ParameterDetailRoute {...props} />;
    case "failure-surface":
      return <FailureSurfaceRoute {...props} />;
    case "optimization":
      return <OptimizationLabRoute {...props} />;
    case "capsule-lab":
      return <CapsuleLabRoute {...props} />;
    case "mission-feasibility":
      return <MissionFeasibilityRoute {...props} />;
    case "mission-runs":
      return <UserMissionRunRoute {...props} />;
    case "cost-feasibility":
      return <CostFeasibilityRoute {...props} />;
    case "mission-probability":
      return <MissionProbabilityCouplingRoute {...props} />;
    case "uncertainty-interactions":
      return <UncertaintyInteractionsRoute {...props} />;
    case "evidence-campaign":
      return <EvidenceCampaignRoute {...props} />;
    case "mission-dag-boundary":
      return <MissionDagBoundaryRoute {...props} />;
    case "external-review":
      return <ExternalReviewRoute {...props} />;
    case "external-proof":
      return <ExternalProofRoute {...props} />;
    case "public-narrative":
      return <PublicNarrativeRoute {...props} />;
    case "roadmap-closure":
      return <RoadmapClosureRoute {...props} />;
    case "not-found":
      return <NotFoundRoute {...props} />;
    default:
      return <NotFoundRoute {...props} />;
  }
}

export default function App(): JSX.Element {
  const { navigate, route } = useHashRoute();
  const currentTitle = routeTitle(route);

  return (
    <div className="app-shell app-frame">
      <header className="hero app-hero">
        <p className="eyebrow">Interstellar Archive Concept</p>
        <h1>{currentTitle}</h1>
        <p className="hero-copy">
          Deterministic mission reasoning with explicit evidence, parameter, and frontier surfaces.
        </p>
        <nav className="workspace-nav" aria-label="Workspace sections">
          {WORKSPACE_NAV_ITEMS.map((item) => {
            const active = isActiveRoute(route, item.route.kind);
            const href = buildRouteHash(item.route);
            return (
              <a
                key={item.label}
                href={href}
                className={`workspace-nav-button${active ? " active" : ""}`}
                aria-current={active ? "page" : undefined}
                onClick={(event) => {
                  event.preventDefault();
                  navigate(item.route);
                }}
              >
                {item.label}
              </a>
            );
          })}
        </nav>
      </header>

      <Suspense fallback={<LoadingPanel label={currentTitle} />}>{renderRoute(route, navigate)}</Suspense>
    </div>
  );
}
