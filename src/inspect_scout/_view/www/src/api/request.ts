import { asyncJsonParse } from "../utils/json-worker";

type HttpMethod = "GET" | "POST" | "PUT" | "DELETE" | "HEAD";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export interface Request<T> {
  headers?: Record<string, string>;
  body?: string;
  parse?: (text: string) => Promise<T>;
  handleError?: (status: number) => T | undefined;
  /**
   * Opt into browser caching. Only use for endpoints that set appropriate caching
   * headers (e.g., ETag). Caching is disabled by default.
   */
  enableBrowserCache?: boolean;
}

export type HeaderProvider = () => Promise<Record<string, string>>;

export interface ServerRequestApi {
  fetchString: (
    method: HttpMethod,
    path: string,
    headers?: Record<string, string>,
    body?: string
  ) => Promise<{ raw: string }>;
  fetchBytes: (
    method: HttpMethod,
    path: string,
    headers?: Record<string, string>,
    extraAcceptType?: string
  ) => Promise<{ data: ArrayBuffer; headers: Headers }>;
  fetchType: <T>(
    method: HttpMethod,
    path: string,
    request?: Request<T>
  ) => Promise<{ raw: string; parsed: T; headers: Headers }>;
}

export function serverRequestApi(
  baseUrl?: string,
  getHeaders?: HeaderProvider,
  customFetch?: typeof fetch
): ServerRequestApi {
  const fetchFn = customFetch ?? fetch;
  const apiUrl = baseUrl || "";

  function buildApiUrl(path: string): string {
    if (!apiUrl) {
      return path;
    }
    const base = apiUrl.endsWith("/") ? apiUrl.slice(0, -1) : apiUrl;
    const cleanPath = path.startsWith("/") ? path : `/${path}`;
    return base + cleanPath;
  }

  function isApiCrossOrigin(): boolean {
    try {
      return Boolean(
        apiUrl && new URL(apiUrl).origin !== window.location.origin
      );
    } catch (error) {
      return false;
    }
  }

  const withGlobalHeaders = async (
    headers: Record<string, string>
  ): Promise<Record<string, string>> =>
    // NOTE: It's typically not safe to use object spreading for headers since,
    // in the general case, they could be HeadersInit which is more complex than
    // Record<string, string>. We're in complete control, so we'll just spread.
    getHeaders ? { ...(await getHeaders()), ...headers } : headers;

  const fetchType = async <T>(
    method: HttpMethod,
    path: string,
    request?: Request<T>
  ): Promise<{ raw: string; parsed: T; headers: Headers }> => {
    const url = buildApiUrl(path);

    // By default, disable browser caching. When enableBrowserCache is true,
    // omit these headers to let the browser handle ETag-based caching.
    const baseHeaders = request?.enableBrowserCache
      ? {
          Accept: "application/json",
          ...request?.headers,
        }
      : {
          Accept: "application/json",
          Pragma: "no-cache",
          Expires: "0",
          "Cache-Control": "no-cache",
          ...request?.headers,
        };

    if (request?.body) {
      baseHeaders["Content-Type"] = "application/json";
    }

    const headers = await withGlobalHeaders(baseHeaders);

    const response = await fetchFn(url, {
      method,
      headers,
      body: request?.body,
      credentials: isApiCrossOrigin() ? "include" : "same-origin",
    });

    if (!response.ok) {
      const errorResponse = request?.handleError?.(response.status);
      if (errorResponse) {
        return {
          raw: response.statusText,
          parsed: errorResponse,
          headers: response.headers,
        };
      }

      const message = (await response.text()) || response.statusText;
      throw new ApiError(
        response.status,
        `API Error ${response.status}: ${message}`
      );
    }

    const text = await response.text();
    const parse = request?.parse || asyncJsonParse;
    return {
      parsed: (await parse(text)) as T,
      raw: text,
      headers: response.headers,
    };
  };

  const fetchString = async (
    method: HttpMethod,
    path: string,
    customHeaders?: Record<string, string>,
    body?: string
  ): Promise<{ raw: string }> => {
    const url = buildApiUrl(path);

    const baseHeaders = {
      Accept: "application/json",
      Pragma: "no-cache",
      Expires: "0",
      "Cache-Control": "no-cache",
      ...customHeaders,
    };

    if (body) {
      baseHeaders["Content-Type"] = "application/json";
    }

    const headers = await withGlobalHeaders(baseHeaders);

    const response = await fetchFn(url, {
      method,
      headers,
      body,
      credentials: isApiCrossOrigin() ? "include" : "same-origin",
    });

    if (response.ok) {
      return { raw: await response.text() };
    }

    const message = (await response.text()) || response.statusText;
    throw new ApiError(response.status, `HTTP ${response.status}: ${message}`);
  };

  /**
   * Fetch binary data from an endpoint.
   *
   * @param extraAcceptType - Additional MIME type to include in Accept header.
   *   Use when an endpoint may return different content types depending on
   *   request headers or server state. For example, an endpoint that returns
   *   application/octet-stream when the client requests raw compressed bytes,
   *   but falls back to application/json when transcoding to browser-compatible
   *   compression.
   */
  const fetchBytes = async (
    method: HttpMethod,
    path: string,
    headers?: Record<string, string>,
    extraAcceptType?: string
  ): Promise<{ data: ArrayBuffer; headers: Headers }> => {
    const url = buildApiUrl(path);
    const acceptTypes = extraAcceptType
      ? `application/octet-stream, ${extraAcceptType}`
      : "application/octet-stream";

    const response = await fetchFn(url, {
      method,
      headers: await withGlobalHeaders({
        Accept: acceptTypes,
        Pragma: "no-cache",
        Expires: "0",
        "Cache-Control": "no-cache",
        ...headers,
      }),
      credentials: isApiCrossOrigin() ? "include" : "same-origin",
    });

    if (!response.ok) {
      const message = (await response.text()) || response.statusText;
      throw new ApiError(
        response.status,
        `HTTP ${response.status}: ${message}`
      );
    }

    return {
      data: await response.arrayBuffer(),
      headers: response.headers,
    };
  };

  return {
    fetchString,
    fetchBytes,
    fetchType,
  };
}
