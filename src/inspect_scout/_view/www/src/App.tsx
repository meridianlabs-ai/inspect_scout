import { FC, useMemo } from "react";
import { RouterProvider } from "react-router-dom";

import "prismjs";
import "prismjs/components/prism-bash";
import "prismjs/components/prism-clike";
import "prismjs/components/prism-javascript";
import "prismjs/components/prism-json";
import "prismjs/components/prism-python";
import "prismjs/themes/prism.css";
import "./app/App.css";
import { useServerTranscriptsDirAsync } from "./app/server/hooks";
import { createAppRouter } from "./AppRouter";

export interface AppProps {
  mode?: "scans" | "workbench";
}

export const App: FC<AppProps> = ({ mode = "scans" }) => {
  const router = useMemo(() => createAppRouter({ mode }), [mode]);
  const { data: transcriptsDir } = useServerTranscriptsDirAsync();

  return transcriptsDir ? <RouterProvider router={router} /> : null;
};
