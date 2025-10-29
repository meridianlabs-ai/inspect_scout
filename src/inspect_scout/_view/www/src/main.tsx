import { createRoot } from "react-dom/client";
import { App } from "./App";
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap-icons/font/bootstrap-icons.css";
import { apiScoutServer } from "./api/api-scout-server";
import { getVscodeApi } from "./utils/vscode";
import { webViewJsonRpcClient } from "./api/jsonrpc";
import { apiVscode } from "./api/api-vscode";
import { ScanApi } from "./api/api";

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
    return apiVscode(vscodeClient);
  } else {
    return apiScoutServer();
  }
};

// Render the app
root.render(<App api={selectApi()} />);
