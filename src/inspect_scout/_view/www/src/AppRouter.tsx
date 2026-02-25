import { FC, lazy, Suspense, useEffect } from "react";
import {
  createHashRouter,
  Outlet,
  useLocation,
  useParams,
} from "react-router-dom";

import { ActivityBarLayout } from "./app/components/ActivityBarLayout";
import { useAppConfig } from "./app/server/useAppConfig";
import { FindBand } from "./components/FindBand";
import { LoadingBar } from "./components/LoadingBar";
import {
  LoggingNavigate,
  useLoggingNavigate,
} from "./debugging/navigationDebugging";
import { useWindowMessaging } from "./hooks/useWindowMessaging";
import {
  kScansRootRouteUrlPattern,
  kScansRouteUrlPattern,
  kScansWithPathRouteUrlPattern,
  kScanRouteUrlPattern,
  isValidScanPath,
  parseScanParams,
  kTranscriptsRouteUrlPattern,
  kTranscriptDetailRoute,
  kProjectRouteUrlPattern,
  kTimelineRouteUrlPattern,
  kValidationRouteUrlPattern,
  scanResultRoute,
  scanRoute,
  scansRoute,
} from "./router/url";
import { useStore } from "./state/store";
import { AppConfig } from "./types/api-types";

const ScansPanel = lazy(() =>
  import("./app/scans/ScansPanel").then((m) => ({ default: m.ScansPanel }))
);
const ScanPanel = lazy(() =>
  import("./app/scan/ScanPanel").then((m) => ({ default: m.ScanPanel }))
);
const ScannerResultPanel = lazy(() =>
  import("./app/scannerResult/ScannerResultPanel").then((m) => ({
    default: m.ScannerResultPanel,
  }))
);
const TranscriptsPanel = lazy(() =>
  import("./app/transcripts/TranscriptsPanel").then((m) => ({
    default: m.TranscriptsPanel,
  }))
);
const TranscriptPanel = lazy(() =>
  import("./app/transcript/TranscriptPanel").then((m) => ({
    default: m.TranscriptPanel,
  }))
);
const ProjectPanel = lazy(() =>
  import("./app/project/ProjectPanel").then((m) => ({
    default: m.ProjectPanel,
  }))
);
const ValidationPanel = lazy(() =>
  import("./app/validation/ValidationPanel").then((m) => ({
    default: m.ValidationPanel,
  }))
);
const RunScanPanel = lazy(() =>
  import("./app/runScan/RunScanPanel").then((m) => ({
    default: m.RunScanPanel,
  }))
);
const TimelinePanel = lazy(() =>
  import("./app/timeline/TimelinePanel").then((m) => ({
    default: m.TimelinePanel,
  }))
);

export interface AppRouterConfig {
  mode: "scans" | "workbench";
  config: AppConfig;
}

// Creates a layout component that handles embedded state and tracks route changes
const createAppLayout = (routerConfig: AppRouterConfig) => {
  const AppLayout = () => {
    const showFind = useStore((state) => state.showFind);
    const setShowFind = useStore((state) => state.setShowFind);
    const singleFileMode = useStore((state) => state.singleFileMode);
    const config = useAppConfig();

    useFindBandShortcut();
    useWindowMessaging();
    useRoutingInitializer(config.scans.dir);

    const content = (
      <Suspense fallback={<LoadingBar loading />}>
        <Outlet />
      </Suspense>
    );
    return (
      <>
        {showFind && (
          <FindBand
            onClose={() => {
              setShowFind(false);
            }}
          />
        )}

        {routerConfig.mode === "workbench" && !singleFileMode ? (
          <ActivityBarLayout config={config}>{content}</ActivityBarLayout>
        ) : (
          content
        )}
      </>
    );
  };

  return AppLayout;
};

// Wrapper component that validates scan path before rendering
const ScanOrScanResultsRoute = () => {
  const params = useParams<{ scansDir?: string; "*": string }>();
  const { scansDir, relativePath, scanResultUuid } = parseScanParams(params);

  // If there's a scan result UUID, render the ScanResultPanel
  if (scanResultUuid) {
    return <ScannerResultPanel />;
  }

  // Validate that the path ends with the correct scan_id pattern
  if (!isValidScanPath(relativePath)) {
    // Redirect to /scans preserving the path structure
    return (
      <LoggingNavigate
        to={scansDir ? scansRoute(scansDir, relativePath) : "/scans"}
        replace
        reason="Invalid scan path"
      />
    );
  }

  return <ScanPanel />;
};

const ProjectPanelRoute = () => {
  const config = useAppConfig();
  return <ProjectPanel config={config} />;
};

export const createAppRouter = (config: AppRouterConfig) => {
  const AppLayout = createAppLayout(config);
  const transcriptsDir = config.config.transcripts;

  return createHashRouter(
    [
      {
        path: "/",
        element: <AppLayout />,
        children: [
          {
            index: true,
            element: <RootIndexRedirect transcriptsDir={transcriptsDir} />,
          },
          {
            path: kScansRootRouteUrlPattern,
            element: <ScansPanel />,
          },
          {
            path: kScansRouteUrlPattern,
            element: <ScansPanel />,
          },
          {
            path: kScansWithPathRouteUrlPattern,
            element: <ScansPanel />,
          },
          {
            path: kScanRouteUrlPattern,
            element: <ScanOrScanResultsRoute />,
          },
          {
            path: kTranscriptsRouteUrlPattern,
            element: <TranscriptsPanel />,
          },
          {
            path: kProjectRouteUrlPattern,
            element: <ProjectPanelRoute />,
          },
          {
            path: kValidationRouteUrlPattern,
            element: <ValidationPanel />,
          },
          {
            path: kTranscriptDetailRoute,
            element: <TranscriptPanel />,
          },
          {
            path: kTimelineRouteUrlPattern,
            element: <TimelinePanel />,
          },
          {
            path: "/run",
            element: <RunScanPanel />,
          },
        ],
      },
      {
        path: "*",
        element: <LoggingNavigate to="/scans" replace reason="catch-all" />,
      },
    ],
    { basename: "" }
  );
};

// Handles routing initialization on first load
const useRoutingInitializer = (serverScansDir: string | undefined) => {
  const navigate = useLoggingNavigate("useRoutingInitializer");
  const hasInitializedRouting = useStore(
    (state) => state.hasInitializedRouting
  );
  const setHasInitializedRouting = useStore(
    (state) => state.setHasInitializedRouting
  );
  const displayedScanResult = useStore((state) => state.displayedScanResult);
  const selectedScanLocation = useStore((state) => state.selectedScanLocation);
  const userScansDir = useStore((state) => state.userScansDir);

  useEffect(() => {
    if (hasInitializedRouting) {
      return;
    }

    const currentPath = window.location.hash.slice(1);
    const isDefaultRoute =
      currentPath === "/" ||
      currentPath === "/scans" ||
      currentPath === "" ||
      currentPath === "/transcripts";

    const resolvedScansDir = userScansDir || serverScansDir;
    if (isDefaultRoute && selectedScanLocation && resolvedScansDir) {
      if (displayedScanResult) {
        void navigate(
          scanResultRoute(
            resolvedScansDir,
            selectedScanLocation,
            displayedScanResult
          ),
          { replace: true }
        );
      } else {
        void navigate(scanRoute(resolvedScansDir, selectedScanLocation), {
          replace: true,
        });
      }
    }

    setHasInitializedRouting(true);
  }, [
    hasInitializedRouting,
    selectedScanLocation,
    displayedScanResult,
    navigate,
    setHasInitializedRouting,
    serverScansDir,
    userScansDir,
  ]);
};

// Global keyboard shortcut to open FindBand
const useFindBandShortcut = () => {
  const setShowFind = useStore((state) => state.setShowFind);
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "f") {
        e.preventDefault();
        setShowFind(true);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [setShowFind]);
};

// Guard against redirecting when a navigation is already in-flight
// (window.location updated but router state hasn't reconciled yet)
const RootIndexRedirect: FC<{
  transcriptsDir: AppConfig["transcripts"];
}> = ({ transcriptsDir }) => {
  const { pathname, search, hash } = useLocation();
  const routerPath = pathname + search + hash;
  const hashPath = window.location.hash.slice(1) || "/";

  return hashPath === routerPath ? (
    <LoggingNavigate
      to={transcriptsDir ? "/transcripts" : "/scans"}
      replace
      reason="Root index redirect"
    />
  ) : null;
};
