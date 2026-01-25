# VS Code HTTP Proxy: V1 → V2 API Migration

## Goal
Replace per-method JSON-RPC handlers with generic HTTP proxy. VS Code mode uses V2 API via single `http_request` RPC method.

## Constraints
- Extension must support old Scout servers (V1 fallback)
- SSE deferred (CSP issues or polling fallback - leave TODO)
- Capability advertised via embedded state

---

## E2E Request Flow: `useScans` Example

Trace a `getScans` call from React hook → Scout server → response.

### Current Flow (V1 Legacy - VS Code)

```
1. ScansPanel.tsx renders
   ↓
2. useScans(scansDir) hook [www/src/app/server/useScans.ts:11]
   - calls api.getScans(scansDir) via React Query
   ↓
3. useApi() returns ScanApi from ApiContext [www/src/state/store.ts:672]
   - main.tsx selected apiVscode() at startup
   ↓
4. apiVscode.getScans() [www/src/api/api-vscode.ts:100]
   - calls fetchScansData() → rpcClient(kMethodGetScans, [])
   ↓
5. webViewJsonRpcClient [www/src/api/jsonrpc.ts:63]
   - vscode.postMessage({ jsonrpc: "2.0", method: "get_scans", params: [] })
   ↓
6. Extension: scanview-panel.ts onDidReceiveMessage
   - methodsMap["get_scans"] → server.getScans()
   ↓
7. ScoutViewServer.getScans() [vscode/.../scout-view-server.ts]
   - HTTP GET http://localhost:7776/api/scans (V1!)
   ↓
8. Scout Python server processes, returns JSON
   ↓
9. Extension: postMessage({ jsonrpc: "2.0", id, result: json })
   ↓
10. jsonrpc.ts resolves promise → apiVscode parses → useScans receives data
```

### New Flow (V2 Proxy - VS Code)

```
1. ScansPanel.tsx renders
   ↓
2. useScans(scansDir) hook [www/src/app/server/useScans.ts:11]
   - calls api.getScans(scansDir) via React Query
   ↓
3. useApi() returns ScanApi from ApiContext
   - main.tsx detected supportsHttpProxy, selected apiScoutServer(proxyFetch)
   ↓
4. apiScoutServer.getScans() [www/src/api/api-scout-server.ts:93]
   - requestApi.fetchString("POST", `/scans/${encodeBase64Url(scansDir)}`, {}, body)
   ↓
5. serverRequestApi.fetchString() [www/src/api/request.ts:133]
   - normally calls fetch(url, {...})
   - WITH proxyFetch: calls proxyFetch(url, {...})
   ↓
6. proxyFetch() [NEW: www/src/api/proxy-fetch.ts]
   - converts fetch args to HttpProxyRequest
   - calls rpcClient("http_request", [{ method: "POST", path: "/scans/...", body: "..." }])
   ↓
7. webViewJsonRpcClient [www/src/api/jsonrpc.ts]
   - vscode.postMessage({ jsonrpc: "2.0", method: "http_request", params: [...] })
   ↓
8. Extension: scanview-panel.ts onDidReceiveMessage
   - methodsMap["http_request"] → server.httpRequest(request)
   ↓
9. ScoutViewServer.httpRequest() [NEW: vscode/.../scout-view-server.ts]
   - HTTP POST http://localhost:7776/api/v2/scans/... (V2!)
   ↓
10. Scout Python server processes V2 endpoint, returns JSON
    ↓
11. Extension: builds HttpProxyResponse { status, headers, body, bodyEncoding }
    - postMessage({ jsonrpc: "2.0", id, result: response })
    ↓
12. proxyFetch() reconstructs Response object from HttpProxyResponse
    ↓
13. serverRequestApi.fetchString() continues normally (text(), parse, etc.)
    ↓
14. apiScoutServer.getScans() returns ScansResponse → useScans receives data
```

### Key Differences

| Aspect | V1 Legacy | V2 Proxy |
|--------|-----------|----------|
| API impl | `apiVscode` (custom) | `apiScoutServer` (reused) |
| RPC methods | Per-endpoint (`get_scans`, `get_scan`, ...) | Single (`http_request`) |
| Backend API | `/api/scans` (V1) | `/api/v2/scans/{dir}` (V2) |
| New endpoint support | Requires 3 code changes | Zero changes |

---

## JSON-RPC Message Routing

How postMessage JSON-RPC works between webview and extension.

### Protocol

JSON-RPC 2.0 over `postMessage`. Each request has unique `id` for response correlation.

```typescript
// Request (webview → extension)
{ jsonrpc: "2.0", id: 12345, method: "get_scans", params: [] }

// Response (extension → webview)
{ jsonrpc: "2.0", id: 12345, result: "{...json...}" }

// Error response
{ jsonrpc: "2.0", id: 12345, error: { code: -32601, message: "Method not found" } }
```

### Webview Side (Frontend)

**Client creation** [www/src/api/jsonrpc.ts:63-81]:
```typescript
export function webViewJsonRpcClient(vscode: VSCodeApi) {
  const target: PostMessageTarget = {
    postMessage: (data) => vscode.postMessage(data),
    onMessage: (handler) => {
      const onMessage = (ev: MessageEvent) => handler(ev.data);
      window.addEventListener("message", onMessage);
      return () => window.removeEventListener("message", onMessage);
    },
  };
  return jsonRpcPostMessageRequestTransport(target).request;
}
```

**Request/response tracking** [www/src/api/jsonrpc.ts:119-152]:
```typescript
// Map of pending requests: id → { resolve, reject }
const requests = new Map<number, RequestHandlers>();

// Listen for responses
target.onMessage((ev) => {
  const response = asJsonRpcResponse(ev);
  if (response) {
    const request = requests.get(response.id);
    if (request) {
      requests.delete(response.id);
      response.error ? request.reject(response.error) : request.resolve(response.result);
    }
  }
});

// Send request, return promise
request: (method, params) => {
  return new Promise((resolve, reject) => {
    const requestId = Math.floor(Math.random() * 1e6);
    requests.set(requestId, { resolve, reject });
    target.postMessage({ jsonrpc: "2.0", id: requestId, method, params });
  });
}
```

### Extension Side

**Server setup** [vscode/.../scanview-panel.ts] (conceptual):
```typescript
// Register method handlers
const methodsMap = {
  [kMethodGetScans]: async (params) => server.getScans(),
  [kMethodGetScan]: async (params) => server.getScan(params[0]),
  [kMethodHttpRequest]: async (params) => server.httpRequest(params[0]),  // NEW
};

// Listen for requests from webview
panel.webview.onDidReceiveMessage(async (data) => {
  const request = asJsonRpcRequest(data);
  if (!request) return;

  const method = methodsMap[request.method];
  if (!method) {
    panel.webview.postMessage({
      jsonrpc: "2.0", id: request.id,
      error: { code: -32601, message: `Method '${request.method}' not found` }
    });
    return;
  }

  try {
    const result = await method(request.params || []);
    panel.webview.postMessage({ jsonrpc: "2.0", id: request.id, result });
  } catch (err) {
    panel.webview.postMessage({
      jsonrpc: "2.0", id: request.id,
      error: { code: -32000, message: err.message }
    });
  }
});
```

### Adding New Methods

**V1 approach** (current): Add to 3 places
1. `jsonrpc.ts` - `export const kMethodNewThing = "new_thing";`
2. `api-vscode.ts` - implement method calling `rpcClient(kMethodNewThing, [...])`
3. Extension `scanview-panel.ts` - add handler `[kMethodNewThing]: async (params) => ...`

**V2 proxy approach** (new): Zero changes
- All HTTP requests flow through single `http_request` method
- Extension just forwards to `/api/v2/*`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│ PROXY MODE (new)                                                    │
│ Webview: apiScoutServer (V2) → proxyFetch → http_request RPC        │
│    → Extension: single handler → HTTP /api/v2/* → Scout Server      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ LEGACY MODE (unchanged, for old extensions)                         │
│ Webview: apiVscode → get_scans/get_scan RPC                        │
│    → Extension: per-method handlers → HTTP /api/* (V1) → Scout      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Frontend (inspect_scout)

### 1.1 New: `www/src/api/proxy-fetch.ts`
Create proxied fetch that routes through JSON-RPC:

```typescript
interface HttpProxyRequest {
  method: "GET" | "POST" | "PUT" | "DELETE";
  path: string;  // e.g., "/scans/L3RtcC9zY2Fucw"
  headers?: Record<string, string>;
  body?: string;
}

interface HttpProxyResponse {
  status: number;
  headers: Record<string, string>;
  body: string | null;
  bodyEncoding?: "utf8" | "base64";  // base64 for binary
}

export const kMethodHttpRequest = "http_request";

export function createProxyFetch(
  rpcClient: (method: string, params?: unknown) => Promise<unknown>
): typeof fetch { ... }
```

Binary handling: extension base64-encodes Arrow IPC responses, frontend decodes.

### 1.2 Modify: `www/src/api/api-scout-server.ts`
Extract to allow injecting custom fetch:

```typescript
export const apiScoutServer = (options?: {
  apiBaseUrl?: string;
  customFetch?: typeof fetch;  // NEW
}): ScanApi => { ... }
```

### 1.3 Modify: `www/src/utils/embeddedState.ts`
Add capability field:

```typescript
interface EmbeddedState {
  // existing fields...
  supportsHttpProxy?: boolean;  // NEW
}
```

### 1.4 Modify: `www/src/main.tsx`
Capability detection:

```typescript
const selectApi = (): ScanApi => {
  const vscodeApi = getVscodeApi();
  if (vscodeApi) {
    const rpcClient = webViewJsonRpcClient(vscodeApi);
    const embeddedState = getEmbeddedState();

    if (embeddedState?.supportsHttpProxy) {
      // V2 via proxy
      const proxyFetch = createProxyFetch(rpcClient);
      return apiScoutServer({ apiBaseUrl: "/api/v2", customFetch: proxyFetch });
    }
    // V1 fallback
    return apiVscode(vscodeApi, rpcClient);
  }
  return apiScoutServer();
};
```

### 1.5 Modify: `www/src/api/api-scout-server.ts` - SSE TODO
Add comment in `connectTopicUpdates`:

```typescript
connectTopicUpdates: (onUpdate) => {
  // TODO: SSE not supported in VS Code proxy mode.
  // Options: (1) investigate CSP connect-src for direct SSE,
  // (2) implement polling fallback, (3) extension subscribes
  // to SSE and forwards via postMessage.
  if (options?.customFetch) {
    onUpdate({ "project-config": Date.now().toString() });
    return () => {};
  }
  // existing EventSource implementation...
}
```

---

## Phase 2: Extension (inspect_vscode)

### 2.1 Modify: `src/core/package/view-server.ts`
Add generic HTTP method:

```typescript
protected async apiGeneric(
  path: string,
  method: "GET" | "POST" | "PUT" | "DELETE",
  headers: Record<string, string>,
  body?: string
): Promise<{ status: number; data: string | Uint8Array; headers: Headers }> {
  const response = await fetch(`http://localhost:${this.serverPort_}${path}`, {
    method,
    headers: { ...headers, Authorization: this.serverAuthToken_ },
    body,
  });

  const isBinary = response.headers.get("Content-Type")
    ?.includes("application/vnd.apache.arrow");

  return {
    status: response.status,
    data: isBinary ? new Uint8Array(await response.arrayBuffer()) : await response.text(),
    headers: response.headers,
  };
}
```

### 2.2 Modify: `src/providers/scout/scout-view-server.ts`
Add proxy handler:

```typescript
async httpRequest(request: HttpProxyRequest): Promise<HttpProxyResponse> {
  const url = `/api/v2${request.path}`;
  const result = await this.apiGeneric(url, request.method, request.headers ?? {}, request.body);

  const isBinary = result.data instanceof Uint8Array;
  return {
    status: result.status,
    headers: Object.fromEntries(result.headers.entries()),
    body: isBinary ? btoa(String.fromCharCode(...result.data)) : result.data,
    bodyEncoding: isBinary ? "base64" : "utf8",
  };
}
```

### 2.3 Modify: `src/providers/scanview/scanview-panel.ts`
Register handler:

```typescript
this._rpcDisconnect = webviewPanelJsonRpcServer(panel_, {
  // Keep existing V1 handlers for backward compat...
  [kMethodHttpRequest]: async (params: unknown[]) => {
    return server.httpRequest(params[0] as HttpProxyRequest);
  },
});
```

### 2.4 Modify: webview HTML injection
Inject capability flag in embedded state:

```typescript
// When rendering webview HTML, add to scanview-state:
{ "type": "updateState", "url": "...", "supportsHttpProxy": true }
```

---

## Files Summary

| File | Change |
|------|--------|
| `www/src/api/proxy-fetch.ts` | NEW - proxied fetch impl |
| `www/src/api/api-scout-server.ts` | Add `customFetch` option, SSE TODO |
| `www/src/utils/embeddedState.ts` | Add `supportsHttpProxy` type |
| `www/src/main.tsx` | Capability detection |
| `vscode/.../view-server.ts` | Add `apiGeneric()` |
| `vscode/.../scout-view-server.ts` | Add `httpRequest()` |
| `vscode/.../scanview-panel.ts` | Register `http_request` handler |
| `vscode/.../webview.ts` | Inject capability flag |

---

## Unresolved Questions

1. **Header normalization**: Normalize to lowercase?
2. **Large binary responses**: Base64 doubles size. Acceptable for now?

---

## Verification

### Frontend
```bash
cd src/inspect_scout/_view/www
pnpm typecheck
pnpm lint
pnpm test
```

### Extension
```bash
cd ~/code/inspect_vscode
npm run compile
npm test
```

### E2E
1. Run `scout view` with sample data
2. Open in VS Code extension
3. Verify scans list loads (uses V2 API)
4. Verify scan detail with scanner results (Arrow IPC binary)
5. Test with old extension version (should fall back to V1)
