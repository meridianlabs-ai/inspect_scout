import {
  createHashRouter,
  Navigate,
  Outlet,
} from "react-router-dom";
import { ScanDetail } from "./app/scan-detail/ScanDetail";
import {
  kScansRouteUrlPattern,
  kScanRouteUrlPattern,
} from "./router/url";
import { ScanList } from "./app/scan-list/ScanList";

// Create a layout component that tracks route changes
const AppLayout = () => {
  return <Outlet />;
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
          path: kScanRouteUrlPattern,
          element: <ScanDetail />,
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
