import { createRoot } from "react-dom/client";

import { ScanApi } from "./api/api";
import { apiScoutServer } from "./api/api-scout-server";
import { apiVscode } from "./api/api-vscode";
import { webViewJsonRpcClient } from "./api/jsonrpc";
import { App } from "./App";
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap-icons/font/bootstrap-icons.css";
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

// TODO: When restoring vscode state, look for specific scan from parquet file

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

// Create the API and store
const api = selectApi();
const store = createStore(api);

// Render the app
root.render(
  <ApiProvider value={api}>
    <StoreProvider value={store}>
      <App />
    </StoreProvider>
  </ApiProvider>
);
