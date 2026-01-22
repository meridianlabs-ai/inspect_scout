import { useEffect } from "react";
import {
  createHashRouter,
  Navigate,
  Outlet,
  useParams,
  useNavigate,
} from "react-router-dom";

import { ActivityBarLayout } from "./app/components/ActivityBarLayout";
import { ProjectPanel } from "./app/project/ProjectPanel";
import { RunScanPanel } from "./app/runScan/RunScanPanel";
import { ScanPanel } from "./app/scan/ScanPanel";
import { ScannerResultPanel } from "./app/scannerResult/ScannerResultPanel";
import { ScansPanel } from "./app/scans/ScansPanel";
import { useConfig } from "./app/server/useConfig";
import { TranscriptPanel } from "./app/transcript/TranscriptPanel";
import { TranscriptsPanel } from "./app/transcripts/TranscriptsPanel";
import { ValidationPanel } from "./app/validation/ValidationPanel";
import { FindBand } from "./components/FindBand";
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
    const navigate = useNavigate();

    const showFind = useStore((state) => state.showFind);
    const setShowFind = useStore((state) => state.setShowFind);

    const selectedScanner = useStore((state) => state.selectedScanner);
    const setSingleFileMode = useStore((state) => state.setSingleFileMode);
    const singleFileMode = useStore((state) => state.singleFileMode);
    const hasInitializedEmbeddedData = useStore(
      (state) => state.hasInitializedEmbeddedData
    );
    const hasInitializedRouting = useStore(
      (state) => state.hasInitializedRouting
    );
    const selectedScanResult = useStore((state) => state.selectedScanResult);
    const selectedScanLocation = useStore(
      (state) => state.selectedScanLocation
    );
    const userScansDir = useStore((state) => state.userScansDir);
    const config = useConfig();
    const serverScansDir = config.scans.dir;
    const setSelectedScanner = useStore((state) => state.setSelectedScanner);
    const setHasInitializedEmbeddedData = useStore(
      (state) => state.setHasInitializedEmbeddedData
    );
    const setHasInitializedRouting = useStore(
      (state) => state.setHasInitializedRouting
    );

    const hasRestoredState = selectedScanner !== undefined;

    // Global keyboard shortcut to open FindBand
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

    useEffect(() => {
      if (hasInitializedEmbeddedData) {
        return;
      }

      // Check for embedded state on initial load
      const embeddedState = getEmbeddedScanState();
      if (embeddedState && !hasRestoredState) {
        const { scan, scanner, dir } = embeddedState;

        // Set the results directory in the store
        setSingleFileMode(true);
        if (scanner) {
          setSelectedScanner(scanner);
        }

        // Navigate to the scan
        void navigate(scanRoute(dir, scan), { replace: true });
      }

      setHasInitializedEmbeddedData(true);
    }, [
      navigate,
      hasInitializedEmbeddedData,
      setSingleFileMode,
      setHasInitializedEmbeddedData,
      setSelectedScanner,
      hasRestoredState,
    ]);

    // Handle state-driven navigation on initial load
    useEffect(() => {
      // Only run once on initial mount, after embedded state is handled
      if (hasInitializedRouting) {
        return;
      }

      // Get current path (remove leading '#' from hash)
      const currentPath = window.location.hash.slice(1);
      const isDefaultRoute =
        currentPath === "/" || currentPath === "/scans" || currentPath === "";

      // If we're on a default route and have persisted state, navigate to the appropriate view
      const resolvedScansDir = userScansDir || serverScansDir;
      if (isDefaultRoute && selectedScanLocation && resolvedScansDir) {
        if (selectedScanResult) {
          // Navigate to scan result view
          void navigate(
            scanResultRoute(
              resolvedScansDir,
              selectedScanLocation,
              selectedScanResult
            ),
            { replace: true }
          );
        } else {
          // Navigate to scanner view
          void navigate(scanRoute(resolvedScansDir, selectedScanLocation), {
            replace: true,
          });
        }
      }

      // Mark routing as initialized
      setHasInitializedRouting(true);
    }, [
      hasInitializedEmbeddedData,
      hasInitializedRouting,
      selectedScanner,
      selectedScanLocation,
      selectedScanResult,
      navigate,
      setHasInitializedRouting,
      serverScansDir,
      userScansDir,
    ]);

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
    if (scansDir) {
      return <Navigate to={scansRoute(scansDir, relativePath)} replace />;
    }
    return <Navigate to="/scans" replace />;
  }

  return <ScanPanel />;
};

const ProjectPanelRoute = () => {
  const config = useConfig();
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
              <Navigate
                to={transcriptsDir ? "/transcripts" : "/scans"}
                replace
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
        element: <Navigate to="/scans" replace />,
      },
    ],
    { basename: "" }
  );
};
