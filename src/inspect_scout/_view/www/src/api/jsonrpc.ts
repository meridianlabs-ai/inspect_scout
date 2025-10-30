import { VSCodeApi } from "../utils/vscode";

// Type definitions
interface JsonRpcMessage {
  jsonrpc: string;
  id: number;
}

interface JsonRpcRequest extends JsonRpcMessage {
  method: string;
  params?: unknown;
}

interface JsonRpcResponse extends JsonRpcMessage {
  result?: unknown;
  error?: JsonRpcError;
}

interface JsonRpcError {
  code: number;
  message: string;
  data?: {
    description?: string;
    [key: string]: unknown;
  };
}

interface RequestHandlers {
  resolve: (value: unknown) => void;
  reject: (error: JsonRpcError) => void;
}

interface PostMessageTarget {
  postMessage: (data: unknown) => void;
  onMessage: (handler: (data: unknown) => void) => () => void;
}

// Constants
export const kMethodEvalLogDir = "eval_log_dir";
export const kMethodEvalLogs = "eval_logs";
export const kMethodEvalLogFiles = "eval_log_files";
export const kMethodEvalLog = "eval_log";
export const kMethodEvalLogSize = "eval_log_size";
export const kMethodEvalLogBytes = "eval_log_bytes";
export const kMethodEvalLogHeaders = "eval_log_headers";
export const kMethodPendingSamples = "eval_log_pending_samples";
export const kMethodSampleData = "eval_log_sample_data";
export const kMethodLogMessage = "log_message";

// Scout constants
export const kMethodGetScan = "get_scan";
export const kMethodGetScans = "get_scans";

export const kJsonRpcParseError = -32700;
export const kJsonRpcInvalidRequest = -32600;
export const kJsonRpcMethodNotFound = -32601;
export const kJsonRpcInvalidParams = -32602;
export const kJsonRpcInternalError = -32603;
export const kJsonRpcVersion = "2.0";

export function webViewJsonRpcClient(
  vscode: VSCodeApi
): (method: string, params?: unknown) => Promise<unknown> {
  const target: PostMessageTarget = {
    postMessage: (data: unknown) => {
      vscode.postMessage(data);
    },
    onMessage: (handler: (data: unknown) => void) => {
      const onMessage = (ev: MessageEvent) => {
        handler(ev.data);
      };
      window.addEventListener("message", onMessage);
      return () => {
        window.removeEventListener("message", onMessage);
      };
    },
  };
  return jsonRpcPostMessageRequestTransport(target).request;
}

export function jsonRpcError(
  message: string,
  data?: unknown,
  code?: number
): JsonRpcError {
  let errorData: { description?: string; [key: string]: unknown } | undefined;

  if (data !== undefined) {
    if (typeof data === "string") {
      errorData = { description: data };
    } else if (typeof data === "object" && data !== null) {
      errorData = data as { description?: string; [key: string]: unknown };
    } else {
      errorData = {
        description: JSON.stringify(data),
      };
    }
  }

  return {
    code: code || -3200,
    message,
    data: errorData,
  };
}

export function asJsonRpcError(error: unknown): JsonRpcError {
  if (typeof error === "object" && error !== null) {
    const err = error as { message?: string; data?: unknown; code?: number };
    if (typeof err.message === "string") {
      return jsonRpcError(err.message, err.data, err.code);
    }
  }
  return jsonRpcError(String(error));
}

export function jsonRpcPostMessageRequestTransport(target: PostMessageTarget) {
  const requests = new Map<number, RequestHandlers>();
  const disconnect = target.onMessage((ev: unknown) => {
    const response = asJsonRpcResponse(ev);
    if (response) {
      const request = requests.get(response.id);
      if (request) {
        requests.delete(response.id);
        if (response.error) {
          request.reject(response.error);
        } else {
          request.resolve(response.result);
        }
      }
    }
  });

  return {
    request: (method: string, params?: unknown): Promise<unknown> => {
      return new Promise((resolve, reject) => {
        const requestId = Math.floor(Math.random() * 1e6);
        requests.set(requestId, { resolve, reject });
        const request: JsonRpcRequest = {
          jsonrpc: kJsonRpcVersion,
          id: requestId,
          method,
          params,
        };
        target.postMessage(request);
      });
    },
    disconnect,
  };
}

export function jsonRpcPostMessageServer(
  target: PostMessageTarget,
  methods:
    | { [key: string]: (params: unknown) => Promise<unknown> }
    | ((name: string) => ((params: unknown) => Promise<unknown>) | undefined)
): () => void {
  const lookupMethod =
    typeof methods === "function" ? methods : (name: string) => methods[name];

  return target.onMessage((data: unknown) => {
    const request = asJsonRpcRequest(data);
    if (request) {
      const method = lookupMethod(request.method);
      if (!method) {
        target.postMessage(methodNotFoundResponse(request));
        return;
      }

      method(request.params || [])
        .then((value) => {
          target.postMessage(jsonRpcResponse(request, value));
        })
        .catch((error: unknown) => {
          target.postMessage({
            jsonrpc: request.jsonrpc,
            id: request.id,
            error: asJsonRpcError(error),
          });
        });
    }
  });
}

function isJsonRpcMessage(message: unknown): message is JsonRpcMessage {
  return (
    typeof message === "object" &&
    message !== null &&
    "jsonrpc" in message &&
    "id" in message
  );
}

function isJsonRpcRequest(message: JsonRpcMessage): message is JsonRpcRequest {
  // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
  return (message as JsonRpcRequest).method !== undefined;
}

function asJsonRpcMessage(data: unknown): JsonRpcMessage | null {
  if (isJsonRpcMessage(data) && data.jsonrpc === kJsonRpcVersion) {
    return data;
  }
  return null;
}

function asJsonRpcRequest(data: unknown): JsonRpcRequest | null {
  const message = asJsonRpcMessage(data);
  if (message && isJsonRpcRequest(message)) {
    return message;
  }
  return null;
}

function asJsonRpcResponse(data: unknown): JsonRpcResponse | null {
  const message = asJsonRpcMessage(data);
  if (message) {
    return message as JsonRpcResponse;
  }
  return null;
}

function jsonRpcResponse(
  request: JsonRpcRequest,
  result: unknown
): JsonRpcResponse {
  return {
    jsonrpc: request.jsonrpc,
    id: request.id,
    result,
  };
}

function jsonRpcErrorResponse(
  request: JsonRpcRequest,
  code: number,
  message: string
): JsonRpcResponse {
  return {
    jsonrpc: request.jsonrpc,
    id: request.id,
    error: jsonRpcError(message, undefined, code),
  };
}

function methodNotFoundResponse(request: JsonRpcRequest): JsonRpcResponse {
  return jsonRpcErrorResponse(
    request,
    kJsonRpcMethodNotFound,
    `Method '${request.method}' not found.`
  );
}
