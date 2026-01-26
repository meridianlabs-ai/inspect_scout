// @vitest-environment jsdom
import { describe, expect, it, vi } from "vitest";

import type { HttpProxyRequest, HttpProxyResponse } from "./jsonrpc-fetch";
import { createJsonRpcFetch, kMethodHttpRequest } from "./jsonrpc-fetch";

function mockRpcClient(response: HttpProxyResponse) {
  return vi.fn().mockResolvedValue(response);
}

const validResponse: HttpProxyResponse = {
  status: 200,
  headers: { "content-type": "application/json" },
  body: '{"ok":true}',
};

describe("createJsonRpcFetch", () => {
  describe("HTTP methods", () => {
    it.each([
      [undefined, "GET"],
      ["GET", "GET"],
      ["get", "GET"],
      ["POST", "POST"],
      ["post", "POST"],
      ["PUT", "PUT"],
      ["put", "PUT"],
      ["DELETE", "DELETE"],
      ["delete", "DELETE"],
    ] as const)("method %s becomes %s", async (inputMethod, expectedMethod) => {
      const rpcClient = mockRpcClient(validResponse);
      const fetch = createJsonRpcFetch(rpcClient);

      await fetch("/api/test", inputMethod ? { method: inputMethod } : {});

      const request = rpcClient.mock.calls[0]![1]![0] as HttpProxyRequest;
      expect(request.method).toBe(expectedMethod);
    });

    it("throws for unsupported HTTP method", async () => {
      const rpcClient = mockRpcClient(validResponse);
      const fetch = createJsonRpcFetch(rpcClient);

      await expect(fetch("/api/test", { method: "PATCH" })).rejects.toThrow(
        "Unsupported HTTP method: PATCH"
      );
    });
  });

  describe("URL/path extraction", () => {
    it.each([
      ["/api/test", "/api/test"],
      ["/api/test?foo=bar", "/api/test?foo=bar"],
      ["/api/test?a=1&b=2", "/api/test?a=1&b=2"],
      ["http://localhost/api/test", "/api/test"],
      ["http://localhost/api/test?q=search", "/api/test?q=search"],
    ])("extracts path from %s", async (input, expectedPath) => {
      const rpcClient = mockRpcClient(validResponse);
      const fetch = createJsonRpcFetch(rpcClient);

      await fetch(input);

      const request = rpcClient.mock.calls[0]![1]![0] as HttpProxyRequest;
      expect(request.path).toBe(expectedPath);
    });

    it("handles URL object input", async () => {
      const rpcClient = mockRpcClient(validResponse);
      const fetch = createJsonRpcFetch(rpcClient);

      await fetch(new URL("http://localhost/api/resource?id=123"));

      const request = rpcClient.mock.calls[0]![1]![0] as HttpProxyRequest;
      expect(request.path).toBe("/api/resource?id=123");
    });
  });

  describe("headers conversion", () => {
    it("converts Headers object", async () => {
      const rpcClient = mockRpcClient(validResponse);
      const fetch = createJsonRpcFetch(rpcClient);
      const headers = new Headers();
      headers.set("Authorization", "Bearer token");
      headers.set("Content-Type", "application/json");

      await fetch("/api/test", { headers });

      const request = rpcClient.mock.calls[0]![1]![0] as HttpProxyRequest;
      expect(request.headers).toEqual({
        authorization: "Bearer token",
        "content-type": "application/json",
      });
    });

    it("converts array of header tuples", async () => {
      const rpcClient = mockRpcClient(validResponse);
      const fetch = createJsonRpcFetch(rpcClient);

      await fetch("/api/test", {
        headers: [
          ["X-Custom", "value1"],
          ["X-Other", "value2"],
        ],
      });

      const request = rpcClient.mock.calls[0]![1]![0] as HttpProxyRequest;
      expect(request.headers).toEqual({
        "X-Custom": "value1",
        "X-Other": "value2",
      });
    });

    it("converts plain object headers", async () => {
      const rpcClient = mockRpcClient(validResponse);
      const fetch = createJsonRpcFetch(rpcClient);

      await fetch("/api/test", {
        headers: { "X-Api-Key": "secret", Accept: "application/json" },
      });

      const request = rpcClient.mock.calls[0]![1]![0] as HttpProxyRequest;
      expect(request.headers).toEqual({
        "X-Api-Key": "secret",
        Accept: "application/json",
      });
    });

    it("handles no headers", async () => {
      const rpcClient = mockRpcClient(validResponse);
      const fetch = createJsonRpcFetch(rpcClient);

      await fetch("/api/test");

      const request = rpcClient.mock.calls[0]![1]![0] as HttpProxyRequest;
      expect(request.headers).toEqual({});
    });
  });

  describe("body handling", () => {
    it("passes string body directly", async () => {
      const rpcClient = mockRpcClient(validResponse);
      const fetch = createJsonRpcFetch(rpcClient);

      await fetch("/api/test", { method: "POST", body: '{"data":"value"}' });

      const request = rpcClient.mock.calls[0]![1]![0] as HttpProxyRequest;
      expect(request.body).toBe('{"data":"value"}');
    });

    it("decodes ArrayBuffer body", async () => {
      const rpcClient = mockRpcClient(validResponse);
      const fetch = createJsonRpcFetch(rpcClient);
      const text = "binary data";
      const buffer = new ArrayBuffer(text.length);
      const view = new Uint8Array(buffer);
      for (let i = 0; i < text.length; i++) {
        view[i] = text.charCodeAt(i);
      }

      await fetch("/api/test", { method: "POST", body: buffer });

      const request = rpcClient.mock.calls[0]![1]![0] as HttpProxyRequest;
      expect(request.body).toBe("binary data");
    });

    it("converts other body types via toString", async () => {
      const rpcClient = mockRpcClient(validResponse);
      const fetch = createJsonRpcFetch(rpcClient);

      await fetch("/api/test", { method: "POST", body: 12345 as never });

      const request = rpcClient.mock.calls[0]![1]![0] as HttpProxyRequest;
      expect(request.body).toBe("12345");
    });

    it("handles no body", async () => {
      const rpcClient = mockRpcClient(validResponse);
      const fetch = createJsonRpcFetch(rpcClient);

      await fetch("/api/test");

      const request = rpcClient.mock.calls[0]![1]![0] as HttpProxyRequest;
      expect(request.body).toBeUndefined();
    });
  });

  describe("RPC client invocation", () => {
    it("calls rpcClient with correct method name", async () => {
      const rpcClient = mockRpcClient(validResponse);
      const fetch = createJsonRpcFetch(rpcClient);

      await fetch("/api/test");

      expect(rpcClient).toHaveBeenCalledWith(kMethodHttpRequest, [
        expect.any(Object),
      ]);
    });
  });

  describe("response handling", () => {
    it("returns Response with utf8 body", async () => {
      const rpcClient = mockRpcClient({
        status: 200,
        headers: { "content-type": "text/plain" },
        body: "Hello, World!",
        bodyEncoding: "utf8",
      });
      const fetch = createJsonRpcFetch(rpcClient);

      const response = await fetch("/api/test");

      expect(response.status).toBe(200);
      expect(response.headers.get("content-type")).toBe("text/plain");
      expect(await response.text()).toBe("Hello, World!");
    });

    it("returns Response with base64-decoded body", async () => {
      const rpcClient = mockRpcClient({
        status: 200,
        headers: { "content-type": "application/octet-stream" },
        body: btoa("binary content"),
        bodyEncoding: "base64",
      });
      const fetch = createJsonRpcFetch(rpcClient);

      const response = await fetch("/api/test");

      expect(response.status).toBe(200);
      expect(await response.text()).toBe("binary content");
    });

    it("returns Response with null body", async () => {
      const rpcClient = mockRpcClient({
        status: 204,
        headers: {},
        body: null,
      });
      const fetch = createJsonRpcFetch(rpcClient);

      const response = await fetch("/api/test");

      expect(response.status).toBe(204);
      expect(await response.text()).toBe("");
    });

    it("handles body without explicit encoding (defaults to utf8)", async () => {
      const rpcClient = mockRpcClient({
        status: 200,
        headers: {},
        body: "plain text",
      });
      const fetch = createJsonRpcFetch(rpcClient);

      const response = await fetch("/api/test");

      expect(await response.text()).toBe("plain text");
    });
  });

  describe("error handling", () => {
    const invalidResponses: [unknown, string][] = [
      [null, "null response"],
      [undefined, "undefined response"],
      ["string", "string response"],
      [{}, "missing status"],
      [{ status: 200 }, "missing headers"],
      [{ status: 200, headers: {} }, "missing body"],
      [{ status: "200", headers: {}, body: null }, "non-numeric status"],
      [{ status: 200, headers: "invalid", body: null }, "non-object headers"],
      [{ status: 200, headers: {}, body: 123 }, "non-string body"],
      [
        { status: 200, headers: {}, body: "x", bodyEncoding: "invalid" },
        "invalid bodyEncoding",
      ],
    ];

    it.each(invalidResponses)(
      "throws for invalid response: %s",
      async (invalidResponse) => {
        const rpcClient = vi.fn().mockResolvedValue(invalidResponse);
        const fetch = createJsonRpcFetch(rpcClient);

        await expect(fetch("/api/test")).rejects.toThrow(
          "Invalid HTTP proxy response from extension host"
        );
      }
    );
  });
});
