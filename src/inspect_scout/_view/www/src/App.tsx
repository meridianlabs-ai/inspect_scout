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
import { useConfigAsync } from "./app/server/useConfig";
import { createAppRouter } from "./AppRouter";

export interface AppProps {
  mode?: "scans" | "workbench";
}

export const AppModeContext = createContext<AppProps["mode"]>("scans");

export const App: FC<AppProps> = ({ mode = "scans" }) => {
  const router = useMemo(() => createAppRouter({ mode }), [mode]);
  const { data: config } = useConfigAsync();

  return config ? (
    <AppModeContext.Provider value={mode}>
      <RouterProvider router={router} />
    </AppModeContext.Provider>
  ) : null;
};
