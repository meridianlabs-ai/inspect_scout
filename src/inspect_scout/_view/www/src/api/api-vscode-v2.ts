/**
 * VS Code API implementation for protocol version 2+.
 * Composes apiScoutServer (for HTTP calls via JSON-RPC proxy) with VS Code storage.
 */

import { VSCodeApi } from "../utils/vscode";

import { ScanApi } from "./api";
import { apiScoutServer } from "./api-scout-server";
import { webViewJsonRpcClient } from "./jsonrpc";
import { createJsonRpcFetch } from "./jsonrpc-fetch";
import { createVSCodeStore } from "./vscode-storage";

export const apiVscodeV2 = (vscodeApi: VSCodeApi): ScanApi => {
  const rpcClient = webViewJsonRpcClient(vscodeApi);
  return {
    ...apiScoutServer({
      customFetch: createJsonRpcFetch(rpcClient),
      disableSSE: true,
    }),
    storage: createVSCodeStore(vscodeApi),
    capability: "workbench",
  };
};
