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
import { useAppConfig } from "./app/server/useAppConfig";
import { TranscriptPanel } from "./app/transcript/TranscriptPanel";
import { TranscriptsPanel } from "./app/transcripts/TranscriptsPanel";
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
  scanResultRoute,
  scanRoute,
  scansRoute,
} from "./router/url";
import { useStore } from "./state/store";
import { AppConfig } from "./types/api-types";

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

    const singleFileMode = useStore((state) => state.singleFileMode);
    const hasInitializedRouting = useStore(
      (state) => state.hasInitializedRouting
    );
    const selectedScanResult = useStore((state) => state.selectedScanResult);
    const selectedScanLocation = useStore(
      (state) => state.selectedScanLocation
    );
    const userScansDir = useStore((state) => state.userScansDir);
    const config = useAppConfig();
    const serverScansDir = config.scans.dir;
    const setHasInitializedRouting = useStore(
      (state) => state.setHasInitializedRouting
    );

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
      hasInitializedRouting,
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
