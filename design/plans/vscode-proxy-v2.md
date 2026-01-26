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
| Caching | Duplicate (AsyncCache + react-query) | Single layer (react-query) |

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

### Webview Side: `webViewJsonRpcClient` Deep Dive

Location: [www/src/api/jsonrpc.ts](../../../src/inspect_scout/_view/www/src/api/jsonrpc.ts)

#### Key Components

| Function | Lines | Purpose |
|----------|-------|---------|
| `webViewJsonRpcClient(vscode)` | 63-81 | Entry point; creates RPC client wrapping VSCode postMessage API |
| `jsonRpcPostMessageRequestTransport(target)` | 119-152 | Core transport: request/response tracking via `Map<id, {resolve,reject}>` |
| `jsonRpcPostMessageServer(target, methods)` | 154-185 | Server-side handler (used by extension, not webview) |

#### Architecture

```
webViewJsonRpcClient(vscode)
  │
  ├─► creates PostMessageTarget {
  │     postMessage: vscode.postMessage,
  │     onMessage: window.addEventListener("message", ...)
  │   }
  │
  └─► jsonRpcPostMessageRequestTransport(target)
        │
        ├─► Sets up response listener (lines 121-134)
        │     - Validates JSON-RPC structure via asJsonRpcResponse()
        │     - Looks up pending request by response.id
        │     - Calls resolve(result) or reject(error)
        │
        └─► Returns { request, disconnect }
              - request(method, params) → Promise<unknown>
              - disconnect() removes message listener
```

#### Request Flow (lines 137-148)

```typescript
request: (method: string, params?: unknown): Promise<unknown> => {
  return new Promise((resolve, reject) => {
    const requestId = Math.floor(Math.random() * 1e6);  // Random ID
    requests.set(requestId, { resolve, reject });        // Store handlers
    target.postMessage({                                 // Send to extension
      jsonrpc: "2.0", id: requestId, method, params
    });
  });
}
```

#### Response Flow (lines 121-134)

```typescript
target.onMessage((ev: unknown) => {
  const response = asJsonRpcResponse(ev);  // Validate structure
  if (response) {
    const request = requests.get(response.id);  // Find pending request
    if (request) {
      requests.delete(response.id);  // Cleanup
      if (response.error) {
        request.reject(response.error);
      } else {
        request.resolve(response.result);
      }
    }
  }
});
```

#### Type Definitions (lines 4-36)

```typescript
interface PostMessageTarget {
  postMessage: (data: unknown) => void;
  onMessage: (handler: (data: unknown) => void) => () => void;  // Returns unsubscribe
}

interface RequestHandlers {
  resolve: (value: unknown) => void;
  reject: (error: JsonRpcError) => void;
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

## Phase 1: Remove Duplicate Caching (inspect_scout) ✅ COMPLETE

Independent prerequisite. Can be done and verified before any V2 work.

### Problem

`api-vscode.ts` implements `AsyncCache` with 10s TTL:

```typescript
// api-vscode.ts:28-33
const scansCache = new AsyncCache<{ scans: Status[]; results_dir: string }>(
  cacheTtlMs  // default 10000ms
);
```

But `useScans.ts` already uses react-query:

```typescript
// useScans.ts:15-26
return useAsyncDataFromQuery({
  queryKey: ["scans", scansDir],
  staleTime: 5000,
  refetchInterval: 5000,
});
```

Two overlapping cache layers:
1. **AsyncCache** (10s TTL, promise dedup)
2. **react-query** (5s stale, 5s refetch, promise dedup)

React-query already provides promise deduplication, TTL caching, background refetch, cache invalidation.

### 1.1 Modify: `www/src/api/api-vscode.ts`

Remove `AsyncCache` usage:

```typescript
// DELETE these lines:
import { AsyncCache } from "./api-cache";
const scansCache = new AsyncCache<...>(cacheTtlMs);

// SIMPLIFY fetchScansData to direct RPC call:
const fetchScansData = async (): Promise<...> => {
  const response = (await rpcClient(kMethodGetScans, [])) as string;
  if (response) {
    return JSON5.parse<...>(response);
  }
  throw new Error("Invalid response for getScans");
};

// REMOVE cacheTtlMs parameter from apiVscode signature
```

### 1.2 Delete: `www/src/api/api-cache.ts`

File only used by `api-vscode.ts`. Delete entirely.

### Files Summary (Phase 1)

| File | Change |
|------|--------|
| `www/src/api/api-vscode.ts` | Remove AsyncCache, simplify fetchScansData ✅ |
| `www/src/api/api-scout-server-v1.ts` | Remove AsyncCache, simplify readScans ✅ (also used cache) |
| `www/src/api/api-cache.ts` | DELETE ✅ |

### Verification (Phase 1)

```bash
cd src/inspect_scout/_view/www
pnpm typecheck
pnpm lint
pnpm test
pnpm build
```

E2E: Open VS Code extension, verify scans list still loads correctly.

---

## Phase 2: Frontend HTTP Proxy Infrastructure (inspect_scout) ✅ COMPLETE

Additive changes only—no behavior change until Phase 4 activates.

### 2.1 New: `www/src/api/proxy-fetch.ts` ✅
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

### 2.2 Modify: `www/src/api/api-scout-server.ts` ✅
Add optional parameters:

```typescript
export const apiScoutServer = (options?: {
  apiBaseUrl?: string;
  customFetch?: typeof fetch;  // NEW - defaults to fetch
  disableSSE?: boolean;        // NEW - defaults to false
}): ScanApi => { ... }
```

When `disableSSE` is true, `connectTopicUpdates` uses polling instead of SSE.

### 2.3 Modify: `www/src/utils/embeddedState.ts` ✅
Add `extensionProtocolVersion` field to `EmbeddedScanState`:

```typescript
interface EmbeddedScanState {
  dir: string;
  scan: string;
  scanner?: string;
  /** Protocol version: undefined/1 = legacy V1, 2 = HTTP proxy support */
  extensionProtocolVersion?: number;
}
```

Extension includes `extensionProtocolVersion` in existing `scanview-state` element.

### Verification (Phase 2)
```bash
cd src/inspect_scout/_view/www
pnpm typecheck && pnpm lint && pnpm test && pnpm build
```
E2E: Existing behavior unchanged—VS Code extension still uses V1 path.

---

## Phase 3: Polling Fallback for Topic Updates (inspect_scout) ✅ COMPLETE

Replace SSE-only topic updates with polling fallback for VS Code proxy mode.

### 3.1 Modify: `src/inspect_scout/_view/_api_v2_topics.py` ✅
Add non-streaming `/topics` endpoint:

```python
@router.get(
    "/topics",
    summary="Get current topic versions",
    description="Returns current topic versions dict for polling clients.",
)
async def get_topics() -> dict[InvalidationTopic, str]:
    """Return current topic versions."""
    return get_topic_versions()
```

### 3.2 Modify: `www/src/api/api-scout-server.ts` ✅
Replace no-op with polling when `disableSSE` is true:

```typescript
if (disableSSE) {
  let active = true;
  const poll = async () => {
    const result = await requestApi.fetchString("GET", "/topics");
    if (active) {
      onUpdate(JSON.parse(result.raw) as TopicVersions);
    }
  };
  void poll();
  const intervalId = setInterval(() => void poll(), 10000);
  return () => {
    active = false;
    clearInterval(intervalId);
  };
}
```

Note: Added `active` flag to prevent updates after cleanup (race condition fix).

### Verification (Phase 3)
```bash
# Python
cd src/inspect_scout
make check && make test

# TypeScript
cd src/inspect_scout/_view/www
pnpm typecheck && pnpm lint && pnpm test && pnpm build
```

### Files Summary (Phase 3)
| File | Change |
|------|--------|
| `src/inspect_scout/_view/_api_v2_topics.py` | Add `/topics` GET endpoint ✅ |
| `www/src/api/api-scout-server.ts` | Replace no-op with polling when `disableSSE` is true ✅ |

---

## Phase 4: Client-Side API Selection (inspect_scout)

Switch `main.tsx` to use `apiScoutServer` (with `disableSSE` and `customFetch`) when `extensionProtocolVersion >= 2`. Requires `proxy-fetch.ts` from Phase 2.

### 4.1 New: `www/src/api/proxy-fetch.ts`

Create the proxied fetch implementation:

```typescript
export interface HttpProxyRequest {
  method: "GET" | "POST" | "PUT" | "DELETE";
  path: string;
  headers?: Record<string, string>;
  body?: string;
}

export interface HttpProxyResponse {
  status: number;
  headers: Record<string, string>;
  body: string | null;
  bodyEncoding?: "utf8" | "base64";
}

export const kMethodHttpRequest = "http_request";

export function createProxyFetch(
  rpcClient: (method: string, params?: unknown) => Promise<unknown>
): typeof fetch {
  return async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = typeof input === "string" ? input : input.toString();
    const path = new URL(url, "http://localhost").pathname;

    const request: HttpProxyRequest = {
      method: (init?.method ?? "GET") as HttpProxyRequest["method"],
      path,
      headers: init?.headers as Record<string, string> | undefined,
      body: init?.body as string | undefined,
    };

    const response = (await rpcClient(kMethodHttpRequest, [request])) as HttpProxyResponse;

    const body = response.body
      ? response.bodyEncoding === "base64"
        ? Uint8Array.from(atob(response.body), (c) => c.charCodeAt(0))
        : response.body
      : null;

    return new Response(body, {
      status: response.status,
      headers: response.headers,
    });
  };
}
```

### 4.2 Modify: `www/src/main.tsx`

Add capability detection and API selection:

```typescript
import { getEmbeddedScanState } from "./utils/embeddedState";
import { createProxyFetch } from "./api/proxy-fetch";

const selectApi = (): ScanApi => {
  const vscodeApi = getVscodeApi();
  if (vscodeApi) {
    const rpcClient = webViewJsonRpcClient(vscodeApi);
    const embeddedState = getEmbeddedScanState();

    if ((embeddedState?.extensionProtocolVersion ?? 1) >= 2) {
      // V2 via HTTP proxy
      const proxyFetch = createProxyFetch(rpcClient);
      return apiScoutServer({
        customFetch: proxyFetch,
        disableSSE: true,
      });
    }
    // V1 fallback for older extensions
    return apiVscode(vscodeApi, rpcClient);
  }
  return apiScoutServer();
};
```

### Verification (Phase 4)
```bash
cd src/inspect_scout/_view/www
pnpm typecheck && pnpm lint && pnpm test && pnpm build
```

E2E: Extension still uses V1 (no `extensionProtocolVersion` in state yet).

### Files Summary (Phase 4)
| File | Change |
|------|--------|
| `www/src/api/proxy-fetch.ts` | NEW - proxied fetch impl |
| `www/src/main.tsx` | Add capability detection, switch API based on version |

---

## Phase 5: Extension (inspect_vscode)

### 5.1 Modify: `src/core/package/view-server.ts`
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

### 5.2 Modify: `src/providers/scout/scout-view-server.ts`
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

### 5.3 Modify: `src/providers/scanview/scanview-panel.ts`
Register handler:

```typescript
this._rpcDisconnect = webviewPanelJsonRpcServer(panel_, {
  // Keep existing V1 handlers for backward compat...
  [kMethodHttpRequest]: async (params: unknown[]) => {
    return server.httpRequest(params[0] as HttpProxyRequest);
  },
});
```

### 5.4 Modify: webview HTML injection
Include `extensionProtocolVersion` in existing `scanview-state` element:

```html
<script id="scanview-state" type="application/json">
{"type": "updateState", "url": "...", "extensionProtocolVersion": 2}
</script>
```

---

## Phase 6: E2E Testing

Requires Phase 5 complete (extension must handle `http_request` and set `extensionProtocolVersion: 2`).

---

## Files Summary

### Phase 1: Remove Duplicate Caching
| File | Change |
|------|--------|
| `www/src/api/api-vscode.ts` | Remove AsyncCache, simplify fetchScansData |
| `www/src/api/api-cache.ts` | DELETE |

### Phase 2: Frontend HTTP Proxy Infrastructure ✅
| File | Change |
|------|--------|
| `www/src/api/api-scout-server.ts` | Add optional `customFetch`, `disableSSE` params ✅ |
| `www/src/api/request.ts` | Add optional `customFetch` param to `serverRequestApi` ✅ |
| `www/src/utils/embeddedState.ts` | Add `extensionProtocolVersion` to `EmbeddedScanState` ✅ |

### Phase 3: Polling Fallback ✅
| File | Change |
|------|--------|
| `src/inspect_scout/_view/_api_v2_topics.py` | Add `/topics` GET endpoint ✅ |
| `www/src/api/api-scout-server.ts` | Replace no-op with polling when `disableSSE` is true ✅ |

### Phase 4: Client-Side API Selection
| File | Change |
|------|--------|
| `www/src/api/proxy-fetch.ts` | NEW - proxied fetch impl |
| `www/src/main.tsx` | Add capability detection, switch API based on version |

### Phase 5: Extension
| File | Change |
|------|--------|
| `vscode/.../view-server.ts` | Add `apiGeneric()` |
| `vscode/.../scout-view-server.ts` | Add `httpRequest()` |
| `vscode/.../scanview-panel.ts` | Register `http_request` handler |
| `vscode/.../webview.ts` | Add `extensionProtocolVersion: 2` to `scanview-state` element |

---

## Unresolved Questions

1. **Header normalization**: Normalize to lowercase?
2. **Large binary responses**: Base64 doubles size. Acceptable for now?

---

## Verification

### Phase 1
```bash
cd src/inspect_scout/_view/www
pnpm typecheck && pnpm lint && pnpm test && pnpm build
```
E2E: VS Code extension scans list still loads.

### Phase 2
```bash
cd src/inspect_scout/_view/www
pnpm typecheck && pnpm lint && pnpm test && pnpm build
```
E2E: Existing behavior unchanged—VS Code extension still uses V1.

### Phase 3
```bash
# Python
cd src/inspect_scout
make check && make test

# TypeScript
cd src/inspect_scout/_view/www
pnpm typecheck && pnpm lint && pnpm test && pnpm build
```

### Phase 4
```bash
cd src/inspect_scout/_view/www
pnpm typecheck && pnpm lint && pnpm test && pnpm build
```

### Phase 5
```bash
cd ~/code/inspect_vscode
npm run compile && npm test
```

### Full E2E (after Phase 6)
1. Run `scout view` with sample data
2. Open in VS Code extension
3. Verify scans list loads (uses V2 API)
4. Verify scan detail with scanner results (Arrow IPC binary)
5. Test with old extension version (should fall back to V1)
