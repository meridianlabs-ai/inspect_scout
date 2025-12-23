import { FC, useMemo } from "react";
import { RouterProvider } from "react-router-dom";

import { createAppRouter } from "./AppRouter";
import "prismjs";
import "prismjs/components/prism-bash";
import "prismjs/components/prism-clike";
import "prismjs/components/prism-javascript";
import "prismjs/components/prism-json";
import "prismjs/components/prism-python";
import "prismjs/themes/prism.css";
import "./app/App.css";

export interface AppProps {
  mode?: "scans" | "workbench";
}

export const App: FC<AppProps> = ({ mode = "scans" }) => {
  const router = useMemo(() => createAppRouter({ mode }), [mode]);

  return <RouterProvider router={router} />;
};
