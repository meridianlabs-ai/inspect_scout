// @vitest-environment jsdom
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { createActiveScanInfo } from "../../test/objectFactories";
import { server } from "../../test/setup-msw";
import { createTestWrapper } from "../../test/test-utils";
import type { ActiveScansResponse } from "../../types/api-types";

import { useActiveScans } from "./useActiveScans";

describe("useActiveScans", () => {
  it("returns loading then data on successful fetch", async () => {
    const scanInfo = createActiveScanInfo({
      scan_id: "scan-123",
      metrics: {
        batch_failures: 0,
        batch_pending: 0,
        buffered_scanner_jobs: 0,
        completed_scans: 100,
        memory_usage: 0,
        process_count: 2,
        task_count: 4,
        tasks_idle: 0,
        tasks_parsing: 0,
        tasks_scanning: 0,
      },
    });

    server.use(
      http.get("/api/v2/scans/active", () =>
        HttpResponse.json<ActiveScansResponse>({
          items: { "scan-123": scanInfo },
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

    expect(result.current.data).toEqual({ "scan-123": scanInfo });
  });

  it("handles empty active scans", async () => {
    server.use(
      http.get("/api/v2/scans/active", () =>
        HttpResponse.json<ActiveScansResponse>({ items: {} })
      )
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
        return HttpResponse.json<ActiveScansResponse>({
          items: {},
        });
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
