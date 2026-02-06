// @vitest-environment jsdom
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "../../test/setup-msw";
import { createTestWrapper } from "../../test/test-utils";

import { useActiveScans } from "./useActiveScans";

describe("useActiveScans", () => {
  it("returns loading then data on successful fetch", async () => {
    server.use(
      http.get("/api/v2/scans/active", () =>
        HttpResponse.json({
          items: {
            "scan-123": {
              scan_id: "scan-123",
              metrics: {
                process_count: 2,
                task_count: 4,
                completed_scans: 100,
              },
              last_updated: 1704067200,
            },
          },
        })
      )
    );

    const { result } = renderHook(() => useActiveScans(), {
      wrapper: createTestWrapper(),
    });

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual({
      "scan-123": {
        scan_id: "scan-123",
        metrics: {
          process_count: 2,
          task_count: 4,
          completed_scans: 100,
        },
        last_updated: 1704067200,
      },
    });
  });

  it("handles empty active scans", async () => {
    server.use(
      http.get("/api/v2/scans/active", () => HttpResponse.json({ items: {} }))
    );

    const { result } = renderHook(() => useActiveScans(), {
      wrapper: createTestWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual({});
  });

  it("returns error on server failure", async () => {
    server.use(
      http.get("/api/v2/scans/active", () =>
        HttpResponse.text("Internal Server Error", { status: 500 })
      )
    );

    const { result } = renderHook(() => useActiveScans(), {
      wrapper: createTestWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeDefined();
    expect(result.current.error?.message).toContain("500");
  });

  it("sends GET request to correct endpoint", async () => {
    let capturedMethod: string | undefined;
    let capturedUrl: string | undefined;

    server.use(
      http.get("/api/v2/scans/active", ({ request }) => {
        capturedMethod = request.method;
        capturedUrl = request.url;
        return HttpResponse.json({ items: {} });
      })
    );

    const { result } = renderHook(() => useActiveScans(), {
      wrapper: createTestWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(capturedMethod).toBe("GET");
    expect(capturedUrl).toContain("/api/v2/scans/active");
  });
});
