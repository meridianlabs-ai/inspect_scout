import {
  createHashRouter,
  Navigate,
  Outlet,
  useParams,
  useNavigate,
} from "react-router-dom";
import { useEffect, useState } from "react";
import { ScanDetail } from "./app/scan-detail/ScanDetail";
import {
  kScansRouteUrlPattern,
  kScansWithPathRouteUrlPattern,
  kScanRouteUrlPattern,
  isValidScanPath,
  getRelativePathFromParams,
} from "./router/url";
import { ScanList } from "./app/scan-list/ScanList";
import { getEmbeddedScanState } from "./utils/embeddedState";
import { useStore } from "./state/store";

// Create a layout component that handles embedded state and tracks route changes
const AppLayout = () => {
  const navigate = useNavigate();
  const setResultsDir = useStore((state) => state.setResultsDir);
  const setSingleFileMode = useStore((state) => state.setSingleFileMode);
  const hasInitializedEmbeddedData = useStore((state) => state.hasInitializedEmbeddedData);
  const setHasInitializedEmbeddedData = useStore((state) => state.setHasInitializedEmbeddedData); 


  useEffect(() => {
    if (hasInitializedEmbeddedData) {
      return;
    }

    // Check for embedded state on initial load
    const embeddedState = getEmbeddedScanState();
    if (embeddedState) {
      const { dir, scan } = embeddedState;

      // Set the results directory in the store
      setResultsDir(dir);
      setSingleFileMode(true)

      // Navigate to the scan
      void navigate(`/scan/${scan}`, { replace: true });
    }

    setHasInitializedEmbeddedData(true);
  }, [navigate, hasInitializedEmbeddedData, setSingleFileMode, setHasInitializedEmbeddedData, setResultsDir]);

  return <Outlet />;
};

// Wrapper component that validates scan path before rendering
const ValidatedScanDetail = () => {
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);

  // Validate that the path ends with the correct scan_id pattern
  if (!isValidScanPath(relativePath)) {
    // Redirect to /scans preserving the path structure
    return <Navigate to={`/scans/${relativePath}`} replace />;
  }

  return <ScanDetail />;
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
          element: <ScanList />,
        },
        {
          path: kScansWithPathRouteUrlPattern,
          element: <ScanList />,
        },
        {
          path: kScanRouteUrlPattern,
          element: <ValidatedScanDetail />,
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
