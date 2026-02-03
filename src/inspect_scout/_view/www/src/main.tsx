import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { createRoot } from "react-dom/client";

import "bootstrap-icons/font/bootstrap-icons.css";
import "bootstrap/dist/css/bootstrap.min.css";
import { ScanApi } from "./api/api";
import { apiScoutServer } from "./api/api-scout-server";
import { apiVscodeV1 } from "./api/api-vscode-v1";
import { apiVscodeV2 } from "./api/api-vscode-v2";
import { App } from "./App";
import { ExtendedFindProvider } from "./components/ExtendedFindProvider";
import { ApiProvider, createStore, StoreProvider } from "./state/store";
import { getEmbeddedScanState } from "./utils/embeddedState";
import { defaultRetry } from "./utils/react-query";
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

const selectApi = (): ScanApi => {
  const vscodeApi = getVscodeApi();
  const api = !vscodeApi
    ? apiScoutServer()
    : (getEmbeddedScanState()?.extensionProtocolVersion ?? 1) < 2
      ? apiVscodeV1(vscodeApi)
      : apiVscodeV2(vscodeApi);
  return api;
};

// Create the API, store, and query client
const api = selectApi();
const store = createStore(api);
const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: defaultRetry } },
});

// Read showActivityBar from query parameters
const urlParams = new URLSearchParams(window.location.search);
const scansMode =
  urlParams.get("mode") === "scans" || api.capability === "scans";

// Render the app
root.render(
  <QueryClientProvider client={queryClient}>
    <ApiProvider value={api}>
      <StoreProvider value={store}>
        <ExtendedFindProvider>
          <App mode={scansMode ? "scans" : "workbench"} />
        </ExtendedFindProvider>
      </StoreProvider>
    </ApiProvider>
    <ReactQueryDevtools initialIsOpen={false} />
  </QueryClientProvider>
);
