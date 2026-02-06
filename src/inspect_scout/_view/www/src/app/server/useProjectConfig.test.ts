// @vitest-environment jsdom
import { renderHook, waitFor, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "../../test/setup-msw";
import { createTestWrapper } from "../../test/test-utils";

import { useProjectConfig, useUpdateProjectConfig } from "./useProjectConfig";

const mockConfig = {
  filter: ["task_id = 'test'"],
};

describe("useProjectConfig", () => {
  it("returns config with etag from response headers", async () => {
    server.use(
      http.get("/api/v2/project/config", () =>
        HttpResponse.json(mockConfig, {
          headers: { ETag: '"abc123"' },
        })
      )
    );

    const { result } = renderHook(() => useProjectConfig(), {
      wrapper: createTestWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual({
      config: mockConfig,
      etag: "abc123",
    });
  });

  it("returns empty etag when header is missing", async () => {
    server.use(
      http.get("/api/v2/project/config", () => HttpResponse.json(mockConfig))
    );

    const { result } = renderHook(() => useProjectConfig(), {
      wrapper: createTestWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data?.etag).toBe("");
  });

  it("returns error on server failure", async () => {
    server.use(
      http.get("/api/v2/project/config", () =>
        HttpResponse.text("Server Error", { status: 500 })
      )
    );

    const { result } = renderHook(() => useProjectConfig(), {
      wrapper: createTestWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeDefined();
  });
});

describe("useUpdateProjectConfig", () => {
  it("sends config with If-Match header and returns updated config", async () => {
    let capturedHeaders: Headers | undefined;
    let capturedBody: unknown;

    const updatedConfig = { filter: ["updated"] };

    server.use(
      http.get("/api/v2/project/config", () =>
        HttpResponse.json(mockConfig, {
          headers: { ETag: '"original"' },
        })
      ),
      http.put("/api/v2/project/config", async ({ request }) => {
        capturedHeaders = new Headers(request.headers);
        capturedBody = await request.json();
        return HttpResponse.json(updatedConfig, {
          headers: { ETag: '"updated-etag"' },
        });
      })
    );

    const wrapper = createTestWrapper();

    const { result: configResult } = renderHook(() => useProjectConfig(), {
      wrapper,
    });
    const { result: mutationResult } = renderHook(
      () => useUpdateProjectConfig(),
      { wrapper }
    );

    await waitFor(() => {
      expect(configResult.current.loading).toBe(false);
    });

    await act(() =>
      mutationResult.current.mutateAsync({
        config: updatedConfig,
        etag: "original",
      })
    );

    await waitFor(() => {
      expect(mutationResult.current.isSuccess).toBe(true);
    });

    expect(capturedHeaders?.get("If-Match")).toBe('"original"');
    expect(capturedBody).toEqual(updatedConfig);
  });

  it("updates cache with new config and etag on success", async () => {
    const updatedConfig = { filter: ["updated"] };

    server.use(
      http.get("/api/v2/project/config", () =>
        HttpResponse.json(mockConfig, {
          headers: { ETag: '"v1"' },
        })
      ),
      http.put("/api/v2/project/config", () =>
        HttpResponse.json(updatedConfig, {
          headers: { ETag: '"v2"' },
        })
      )
    );

    const wrapper = createTestWrapper();

    const { result: configResult } = renderHook(() => useProjectConfig(), {
      wrapper,
    });
    const { result: mutationResult } = renderHook(
      () => useUpdateProjectConfig(),
      { wrapper }
    );

    await waitFor(() => {
      expect(configResult.current.loading).toBe(false);
    });

    await act(() =>
      mutationResult.current.mutateAsync({ config: updatedConfig, etag: "v1" })
    );

    await waitFor(() => {
      expect(mutationResult.current.isSuccess).toBe(true);
    });

    // The config query cache should be updated with the new data
    await waitFor(() => {
      expect(configResult.current.data).toEqual({
        config: updatedConfig,
        etag: "v2",
      });
    });
  });

  it("propagates 412 Precondition Failed as error", async () => {
    server.use(
      http.get("/api/v2/project/config", () =>
        HttpResponse.json(mockConfig, {
          headers: { ETag: '"v1"' },
        })
      ),
      http.put("/api/v2/project/config", () =>
        HttpResponse.text("Precondition Failed", { status: 412 })
      )
    );

    const wrapper = createTestWrapper();

    const { result: configResult } = renderHook(() => useProjectConfig(), {
      wrapper,
    });
    const { result: mutationResult } = renderHook(
      () => useUpdateProjectConfig(),
      { wrapper }
    );

    await waitFor(() => {
      expect(configResult.current.loading).toBe(false);
    });

    await act(async () => {
      try {
        await mutationResult.current.mutateAsync({
          config: mockConfig,
          etag: "stale",
        });
      } catch {
        // expected
      }
    });

    await waitFor(() => {
      expect(mutationResult.current.isError).toBe(true);
    });

    expect(mutationResult.current.error?.message).toContain("412");
  });
});
