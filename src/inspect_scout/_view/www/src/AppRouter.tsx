import {
  createHashRouter,
  Navigate,
  Outlet,
  useParams,
} from "react-router-dom";
import { ScanDetail } from "./app/scan-detail/ScanDetail";
import {
  kScansRouteUrlPattern,
  kScansWithPathRouteUrlPattern,
  kScanRouteUrlPattern,
  isValidScanPath,
  getRelativePathFromParams,
} from "./router/url";
import { ScanList } from "./app/scan-list/ScanList";

// Create a layout component that tracks route changes
const AppLayout = () => {
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
