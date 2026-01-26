/**
 * HTTP proxy for VS Code webview environment.
 * Routes fetch requests through JSON-RPC to the extension host.
 */

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

function isHttpProxyResponse(value: unknown): value is HttpProxyResponse {
  if (typeof value !== "object" || value === null) return false;
  if (!("status" in value) || typeof value.status !== "number") return false;
  if (
    !("headers" in value) ||
    typeof value.headers !== "object" ||
    value.headers === null
  )
    return false;
  if (
    !("body" in value) ||
    (typeof value.body !== "string" && value.body !== null)
  )
    return false;
  if (
    "bodyEncoding" in value &&
    value.bodyEncoding !== "utf8" &&
    value.bodyEncoding !== "base64"
  )
    return false;
  return true;
}

function toHttpMethod(method: string): HttpProxyRequest["method"] {
  const upper = method.toUpperCase();
  if (
    upper === "GET" ||
    upper === "POST" ||
    upper === "PUT" ||
    upper === "DELETE"
  ) {
    return upper;
  }
  throw new Error(`Unsupported HTTP method: ${method}`);
}

/**
 * Creates a fetch function that proxies requests through JSON-RPC.
 * Used in VS Code webview to route HTTP requests through the extension host.
 */
export function createJsonRpcFetch(
  rpcClient: (method: string, params?: unknown) => Promise<unknown>
): typeof fetch {
  return async (
    input: RequestInfo | URL,
    init?: RequestInit
  ): Promise<Response> => {
    const url = typeof input === "string" ? input : input.toString();
    const urlObj = new URL(url, window.location.origin);
    const path = urlObj.pathname + urlObj.search;

    const method = toHttpMethod(init?.method ?? "GET");

    // Convert Headers to Record<string, string>
    const headers: Record<string, string> = {};
    if (init?.headers) {
      const headerEntries =
        init.headers instanceof Headers
          ? init.headers.entries()
          : Array.isArray(init.headers)
            ? init.headers
            : Object.entries(init.headers);
      for (const [key, value] of headerEntries) {
        headers[key] = value;
      }
    }

    // Get body as string
    let body: string | undefined;
    if (init?.body) {
      body =
        typeof init.body === "string"
          ? init.body
          : init.body instanceof ArrayBuffer
            ? new TextDecoder().decode(init.body)
            : String(init.body);
    }

    const request: HttpProxyRequest = { method, path, headers, body };
    const response = await rpcClient(kMethodHttpRequest, [request]);
    if (!isHttpProxyResponse(response)) {
      throw new Error("Invalid HTTP proxy response from extension host");
    }

    const responseBody: BodyInit | null =
      response.body === null
        ? null
        : response.bodyEncoding === "base64"
          ? Uint8Array.from(atob(response.body), (c) => c.charCodeAt(0))
          : response.body;

    return new Response(responseBody, {
      status: response.status,
      headers: new Headers(response.headers),
    });
  };
}
