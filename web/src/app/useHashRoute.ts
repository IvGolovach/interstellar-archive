import { useEffect, useState } from "react";

import { buildRouteHash, DEFAULT_ROUTE, parseHashRoute, type AppRoute } from "./app_routes";

function getWindowHash(): string {
  if (typeof window === "undefined") {
    return buildRouteHash(DEFAULT_ROUTE);
  }
  return window.location.hash || buildRouteHash(DEFAULT_ROUTE);
}

export function useHashRoute(): {
  navigate: (route: AppRoute) => void;
  route: AppRoute;
} {
  const [route, setRoute] = useState<AppRoute>(() => parseHashRoute(getWindowHash()));

  useEffect(() => {
    const syncRoute = (): void => {
      setRoute(parseHashRoute(window.location.hash));
    };

    if (!window.location.hash) {
      window.location.hash = buildRouteHash(DEFAULT_ROUTE);
    }

    window.addEventListener("hashchange", syncRoute);
    syncRoute();
    return () => window.removeEventListener("hashchange", syncRoute);
  }, []);

  const navigate = (nextRoute: AppRoute): void => {
    const nextHash = buildRouteHash(nextRoute);
    if (window.location.hash !== nextHash) {
      window.location.hash = nextHash;
    }
  };

  return { navigate, route };
}
