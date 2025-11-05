import { FC, useEffect } from "react";
import { RouterProvider } from "react-router-dom";

import { ScanApi } from "./api/api";
import { AppRouter } from "./AppRouter";
import { useStore } from "./state/store";
import "prismjs";
import "prismjs/components/prism-bash";
import "prismjs/components/prism-clike";
import "prismjs/components/prism-javascript";
import "prismjs/components/prism-json";
import "prismjs/components/prism-python";
import "prismjs/themes/prism.css";
import "./app/App.css";

export interface AppProps {
  api: ScanApi;
}

export const App: FC<AppProps> = ({ api }) => {
  useEffect(() => {
    useStore.getState().setApi(api);
  }, [api]);

  return <RouterProvider router={AppRouter} />;
};
