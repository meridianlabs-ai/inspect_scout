import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { createRoot } from "react-dom/client";

import "bootstrap-icons/font/bootstrap-icons.css";
import "bootstrap/dist/css/bootstrap.min.css";
import { ScanApi } from "./api/api";
import { apiScoutServer } from "./api/api-scout-server";
import { apiVscode } from "./api/api-vscode";
import { webViewJsonRpcClient } from "./api/jsonrpc";
import { createJsonRpcFetch } from "./api/jsonrpc-fetch";
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

// Select the API client
const selectApi = (): ScanApi => {
  const vscodeApi = getVscodeApi();
  if (vscodeApi) {
    const rpcClient = webViewJsonRpcClient(vscodeApi);
    const embeddedState = getEmbeddedScanState();

    if ((embeddedState?.extensionProtocolVersion ?? 1) >= 2) {
      // V2: HTTP proxy via JSON-RPC
      const jsonRpcFetch = createJsonRpcFetch(rpcClient);
      return apiScoutServer({ customFetch: jsonRpcFetch, disableSSE: true });
    }
    // V1 fallback for older extensions
    return apiVscode(vscodeApi, rpcClient);
  }
  return apiScoutServer();
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
