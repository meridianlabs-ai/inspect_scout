import { FC } from "react";
import { RouterProvider } from "react-router-dom";

import { AppRouter } from "./AppRouter";
import "prismjs";
import "prismjs/components/prism-bash";
import "prismjs/components/prism-clike";
import "prismjs/components/prism-javascript";
import "prismjs/components/prism-json";
import "prismjs/components/prism-python";
import "prismjs/themes/prism.css";
import "./app/App.css";

export const App: FC = () => {
  return <RouterProvider router={AppRouter} />;
};
