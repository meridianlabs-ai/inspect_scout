import { useEffect } from "react";
import {
  createHashRouter,
  Navigate,
  Outlet,
  useParams,
  useNavigate,
} from "react-router-dom";

import { ScanResultPanel } from "./app/result/ScanResultPanel";
import { ScanJobsPanel } from "./app/scanJobs/ScanJobsPanel";
import { ScannerPanel } from "./app/scanner/ScannerPanel";
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
  const setResultsDir = useStore((state) => state.setResultsDir);
  const setSingleFileMode = useStore((state) => state.setSingleFileMode);
  const hasInitializedEmbeddedData = useStore(
    (state) => state.hasInitializedEmbeddedData
  );
  const setSelectedScanner = useStore((state) => state.setSelectedScanner);
  const setHasInitializedEmbeddedData = useStore(
    (state) => state.setHasInitializedEmbeddedData
  );

  useEffect(() => {
    if (hasInitializedEmbeddedData) {
      return;
    }

    // Check for embedded state on initial load
    const embeddedState = getEmbeddedScanState();
    if (embeddedState) {
      const { dir, scan, scanner } = embeddedState;

      // Set the results directory in the store
      setResultsDir(dir);
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
    setResultsDir,
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

  return <ScannerPanel />;
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
