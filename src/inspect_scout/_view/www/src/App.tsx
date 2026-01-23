import { FC, createContext, useMemo } from "react";
import { RouterProvider } from "react-router-dom";

import "prismjs";
import "prismjs/components/prism-bash";
import "prismjs/components/prism-clike";
import "prismjs/components/prism-javascript";
import "prismjs/components/prism-json";
import "prismjs/components/prism-python";
import "prismjs/themes/prism.css";
import "./app/App.css";
import { useAppConfigAsync } from "./app/server/useAppConfig";
import { useTopicInvalidation } from "./app/server/useTopicInvalidation";
import { AppErrorBoundary } from "./AppErrorBoundary";
import { createAppRouter } from "./AppRouter";
import { ExtendedFindProvider } from "./components/ExtendedFindProvider";

export const AppModeContext = createContext<AppProps["mode"]>("scans");

export interface AppProps {
  mode?: "scans" | "workbench";
}

export const App: FC<AppProps> = (props) => {
  const invalidationReady = useTopicInvalidation();

  return invalidationReady ? <AppContent {...props} /> : null;
};

const AppContent: FC<AppProps> = ({ mode = "scans" }) => {
  const router = useAppRouter(mode);

  return router ? (
    <AppErrorBoundary>
      <AppModeContext.Provider value={mode}>
        <ExtendedFindProvider>
          <RouterProvider router={router} />
        </ExtendedFindProvider>
      </AppModeContext.Provider>
    </AppErrorBoundary>
  ) : null;
};

const useAppRouter = (mode: "scans" | "workbench") => {
  const { data: appConfig } = useAppConfigAsync();
  return useMemo(
    () => (appConfig ? createAppRouter({ mode, config: appConfig }) : null),
    [mode, appConfig]
  );
};
