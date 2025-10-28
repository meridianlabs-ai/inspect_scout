import { FC, useEffect } from "react";
import { RouterProvider } from "react-router-dom";
import { AppRouter } from "./AppRouter";
import { ScanApi } from "./api/api";
import { useStore } from "./state/store";
import "./App.css";

export interface AppProps {
  api: ScanApi;
}

export const App: FC<AppProps> = ({api}) => {
  useEffect(() => {
    useStore.getState().setApi(api);
  }, [api])

  return <RouterProvider router={AppRouter} />;
};
