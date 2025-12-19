import { useEffect } from "react";
import {
  createHashRouter,
  Navigate,
  Outlet,
  useParams,
  useNavigate,
} from "react-router-dom";

import { ScanJobsPanel } from "./app/scanJobs/ScanJobsPanel";
import { ScanResultPanel } from "./app/scanResults/ScanResultPanel";
import { ScansPanel } from "./app/scans/ScansPanel";
import { AppErrorBoundary } from "./AppErrorBoundary";
import {
  kScansRouteUrlPattern,
  kScansWithPathRouteUrlPattern,
  kScanRouteUrlPattern,
  isValidScanPath,
  getRelativePathFromParams,
  parseScanResultPath,
} from "./router/url";
import { useStore } from "./state/store";
import { getEmbeddedScanState } from "./utils/embeddedState";

// Create a layout component that handles embedded state and tracks route changes
const AppLayout = () => {
  const navigate = useNavigate();
  const selectedScanner = useStore((state) => state.selectedScanner);
  const setSingleFileMode = useStore((state) => state.setSingleFileMode);
  const hasInitializedEmbeddedData = useStore(
    (state) => state.hasInitializedEmbeddedData
  );
  const hasInitializedRouting = useStore(
    (state) => state.hasInitializedRouting
  );
  const selectedScanResult = useStore((state) => state.selectedScanResult);
  const selectedScanLocation = useStore((state) => state.selectedScanLocation);
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
      const { scan, scanner } = embeddedState;

      // Set the results directory in the store
      setSingleFileMode(true);
      if (scanner) {
        setSelectedScanner(scanner);
      }

      // Navigate to the scan
      void navigate(`/scan/${scan}`, { replace: true });
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
    if (isDefaultRoute && selectedScanLocation) {
      if (selectedScanResult) {
        // Navigate to scan result view
        void navigate(`/scan/${selectedScanLocation}/${selectedScanResult}`, {
          replace: true,
        });
      } else {
        // Navigate to scanner view
        void navigate(`/scan/${selectedScanLocation}`, { replace: true });
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
  ]);

  return (
    <AppErrorBoundary>
      <Outlet />
    </AppErrorBoundary>
  );
};

// Wrapper component that validates scan path before rendering
const ScanOrScanResultsRoute = () => {
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);

  // Parse the path to check if it contains a scan result UUID
  const { scanResultUuid } = parseScanResultPath(relativePath);

  // If there's a scan result UUID, render the ScanResultPanel
  if (scanResultUuid) {
    return <ScanResultPanel />;
  }

  // Validate that the path ends with the correct scan_id pattern
  if (!isValidScanPath(relativePath)) {
    // Redirect to /scans preserving the path structure
    return <Navigate to={`/scans/${relativePath}`} replace />;
  }

  return <ScansPanel />;
};

export const AppRouter = createHashRouter(
  [
    {
      path: "/",
      element: <AppLayout />,
      children: [
        {
          index: true,
          element: <Navigate to="/scans" replace />,
        },
        {
          path: kScansRouteUrlPattern,
          element: <ScanJobsPanel />,
        },
        {
          path: kScansWithPathRouteUrlPattern,
          element: <ScanJobsPanel />,
        },
        {
          path: kScanRouteUrlPattern,
          element: <ScanOrScanResultsRoute />,
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
