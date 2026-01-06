import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { createRoot } from "react-dom/client";

import { ScanApi } from "./api/api";
import { apiScoutServer } from "./api/api-scout-server";
import { apiVscode } from "./api/api-vscode";
import { webViewJsonRpcClient } from "./api/jsonrpc";
import { App } from "./App";
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap-icons/font/bootstrap-icons.css";
import { ExtendedFindProvider } from "./components/ExtendedFindProvider";
import { ApiProvider, createStore, StoreProvider } from "./state/store";
import { getVscodeApi } from "./utils/vscode";

// Find the root element and render into it
const containerId = "app";
const container = document.getElementById(containerId);
if (!container) {
  console.error("Root container not found");
  throw new Error(
    `Expected a container element with Id '${containerId}' but no such container element was present.`
  );
}

// Render into the root
const root = createRoot(container);

// Select the API client)
const selectApi = (): ScanApi => {
  const vscodeApi = getVscodeApi();
  if (vscodeApi) {
    const vscodeClient = webViewJsonRpcClient(vscodeApi);
    return apiVscode(vscodeApi, vscodeClient);
  } else {
    return apiScoutServer();
  }
};

// Create the API, store, and query client
const api = selectApi();
const store = createStore(api);
const queryClient = new QueryClient();

// Read showActivityBar from query parameters
const urlParams = new URLSearchParams(window.location.search);
const workbenchMode =
  urlParams.get("workbench") !== null && api.capability === "workbench";

// Render the app
root.render(
  <QueryClientProvider client={queryClient}>
    <ApiProvider value={api}>
      <StoreProvider value={store}>
        <ExtendedFindProvider>
          <App mode={workbenchMode ? "workbench" : "scans"} />
        </ExtendedFindProvider>
      </StoreProvider>
    </ApiProvider>
    <ReactQueryDevtools initialIsOpen={false} />
  </QueryClientProvider>
);
