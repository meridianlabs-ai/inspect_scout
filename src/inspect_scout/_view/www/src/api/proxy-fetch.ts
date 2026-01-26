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

/**
 * Creates a fetch function that proxies requests through JSON-RPC.
 * Used in VS Code webview to route HTTP requests through the extension host.
 */
export function createProxyFetch(
  rpcClient: (method: string, params?: unknown) => Promise<unknown>
): typeof fetch {
  return async (
    input: RequestInfo | URL,
    init?: RequestInit
  ): Promise<Response> => {
    const url = typeof input === "string" ? input : input.toString();
    const urlObj = new URL(url, window.location.origin);
    const path = urlObj.pathname + urlObj.search;

    const method = (
      init?.method ?? "GET"
    ).toUpperCase() as HttpProxyRequest["method"];

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
    const response = (await rpcClient(kMethodHttpRequest, [
      request,
    ])) as HttpProxyResponse;

    // Decode body based on encoding
    let responseBody: BodyInit | null = null;
    if (response.body !== null) {
      if (response.bodyEncoding === "base64") {
        // Decode base64 to binary
        const binary = atob(response.body);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
          bytes[i] = binary.charCodeAt(i);
        }
        responseBody = bytes;
      } else {
        responseBody = response.body;
      }
    }

    return new Response(responseBody, {
      status: response.status,
      headers: new Headers(response.headers),
    });
  };
}
