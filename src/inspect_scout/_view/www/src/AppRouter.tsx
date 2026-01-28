import { FC, useEffect } from "react";
import {
  createHashRouter,
  Outlet,
  useLocation,
  useParams,
} from "react-router-dom";

import { ActivityBarLayout } from "./app/components/ActivityBarLayout";
import { ProjectPanel } from "./app/project/ProjectPanel";
import { RunScanPanel } from "./app/runScan/RunScanPanel";
import { ScanPanel } from "./app/scan/ScanPanel";
import { ScannerResultPanel } from "./app/scannerResult/ScannerResultPanel";
import { ScansPanel } from "./app/scans/ScansPanel";
import { useAppConfig } from "./app/server/useAppConfig";
import { TranscriptPanel } from "./app/transcript/TranscriptPanel";
import { TranscriptsPanel } from "./app/transcripts/TranscriptsPanel";
import { ValidationPanel } from "./app/validation/ValidationPanel";
import { FindBand } from "./components/FindBand";
import {
  LoggingNavigate,
  timestamp,
  useLoggingNavigate,
} from "./debugging/navigationDebugging";
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
  kValidationRouteUrlPattern,
  scanResultRoute,
  scanRoute,
  scansRoute,
} from "./router/url";
import { useStore } from "./state/store";
import { AppConfig } from "./types/api-types";
import { getEmbeddedScanState } from "./utils/embeddedState";

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
    useEmbeddedStateInitializer();
    useRoutingInitializer(config.scans.dir);

    const content = <Outlet />;
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
            element: (
              <LoggingNavigate
                to={transcriptsDir ? "/transcripts" : "/scans"}
                replace
                reason="Root index redirect"
              />
            ),
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

// Handles embedded state initialization on first load
const useEmbeddedStateInitializer = () => {
  const navigate = useLoggingNavigate("useEmbeddedStateInitializer");
  const hasInitializedEmbeddedData = useStore(
    (state) => state.hasInitializedEmbeddedData
  );
  const setHasInitializedEmbeddedData = useStore(
    (state) => state.setHasInitializedEmbeddedData
  );
  const setSingleFileMode = useStore((state) => state.setSingleFileMode);
  const setSelectedScanner = useStore((state) => state.setSelectedScanner);
  const selectedScanner = useStore((state) => state.selectedScanner);

  useEffect(() => {
    if (hasInitializedEmbeddedData) {
      return;
    }

    // Check for embedded state on initial load
    const hasRestoredState = selectedScanner !== undefined;
    if (!hasRestoredState) {
      const embeddedState = getEmbeddedScanState();
      if (embeddedState) {
        const { scan, scanner, dir } = embeddedState;

        // Set the results directory in the store
        setSingleFileMode(true);
        if (scanner) {
          setSelectedScanner(scanner);
        }

        console.log(
          `[${timestamp()}] useEmbeddedStateInitializer.useEffect: navigating to ${scanRoute(dir, scan)}`
        );

        // Navigate to the scan
        void navigate(scanRoute(dir, scan), { replace: true });
      }
    }
    setHasInitializedEmbeddedData(true);
  }, [
    navigate,
    hasInitializedEmbeddedData,
    setSingleFileMode,
    setHasInitializedEmbeddedData,
    selectedScanner,
    setSelectedScanner,
  ]);
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
  const selectedScanResult = useStore((state) => state.selectedScanResult);
  const selectedScanLocation = useStore((state) => state.selectedScanLocation);
  const userScansDir = useStore((state) => state.userScansDir);

  useEffect(() => {
    if (hasInitializedRouting) {
      return;
    }

    const currentPath = window.location.hash.slice(1);
    const isDefaultRoute =
      currentPath === "/" || currentPath === "/scans" || currentPath === "";

    const resolvedScansDir = userScansDir || serverScansDir;
    if (isDefaultRoute && selectedScanLocation && resolvedScansDir) {
      if (selectedScanResult) {
        void navigate(
          scanResultRoute(
            resolvedScansDir,
            selectedScanLocation,
            selectedScanResult
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
    selectedScanResult,
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
