import { useEffect } from "react";
import {
  createHashRouter,
  Navigate,
  Outlet,
  useParams,
  useNavigate,
} from "react-router-dom";

import { ActivityBarLayout } from "./app/components/ActivityBarLayout";
import { ScanPanel } from "./app/scan/ScanPanel";
import { ScannerResultPanel } from "./app/scannerResult/ScannerResultPanel";
import { ScansPanel } from "./app/scans/ScansPanel";
import { useServerScansDir } from "./app/server/hooks";
import { TranscriptPanel } from "./app/transcript/TranscriptPanel";
import { TranscriptsPanel } from "./app/transcripts/TranscriptsPanel";
import { AppErrorBoundary } from "./AppErrorBoundary";
import {
  kScansRootRouteUrlPattern,
  kScansRouteUrlPattern,
  kScansWithPathRouteUrlPattern,
  kScanRouteUrlPattern,
  isValidScanPath,
  parseScanParams,
  kTranscriptsRouteUrlPattern,
  kTranscriptDetailRoute,
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
const createAppLayout = (config: AppRouterConfig) => {
  const AppLayout = () => {
    const navigate = useNavigate();
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
    const serverScansDir = useServerScansDir();
    const setSelectedScanner = useStore((state) => state.setSelectedScanner);
    const setHasInitializedEmbeddedData = useStore(
      (state) => state.setHasInitializedEmbeddedData
    );
    const setHasInitializedRouting = useStore(
      (state) => state.setHasInitializedRouting
    );

    const hasRestoredState = selectedScanner !== undefined;

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
      <AppErrorBoundary>
        {config.mode === "workbench" && !singleFileMode ? (
          <ActivityBarLayout>{content}</ActivityBarLayout>
        ) : (
          content
        )}
      </AppErrorBoundary>
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

export const createAppRouter = (appRouterConfig: AppRouterConfig) => {
  const AppLayout = createAppLayout(appRouterConfig);

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
                to={
                  appRouterConfig.config.transcripts_dir
                    ? "/transcripts"
                    : "/scans"
                }
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
            path: kTranscriptDetailRoute,
            element: <TranscriptPanel />,
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
