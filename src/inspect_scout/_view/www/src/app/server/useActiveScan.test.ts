// @vitest-environment jsdom
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { createActiveScanInfo } from "../../test/objectFactories";
import { server } from "../../test/setup-msw";
import { createTestWrapper } from "../../test/test-utils";
import type { ActiveScansResponse } from "../../types/api-types";

import { useActiveScan } from "./useActiveScan";

const scan123 = createActiveScanInfo({
  scan_id: "scan-123",
  total_scans: 10,
  metrics: {
    batch_failures: 0,
    batch_pending: 0,
    buffered_scanner_jobs: 0,
    completed_scans: 5,
    memory_usage: 0,
    process_count: 0,
    task_count: 0,
    tasks_idle: 0,
    tasks_parsing: 0,
    tasks_scanning: 0,
  },
});

const scan456 = createActiveScanInfo({
  scan_id: "scan-456",
  total_scans: 20,
  metrics: {
    batch_failures: 0,
    batch_pending: 0,
    buffered_scanner_jobs: 0,
    completed_scans: 15,
    memory_usage: 0,
    process_count: 0,
    task_count: 0,
    tasks_idle: 0,
    tasks_parsing: 0,
    tasks_scanning: 0,
  },
});

const activeScanResponse: ActiveScansResponse = {
  items: {
    "scan-123": scan123,
    "scan-456": scan456,
  },
};

describe("useActiveScan", () => {
  it("returns matching scan info when scan is active", async () => {
    server.use(
      http.get("/api/v2/scans/active", () =>
        HttpResponse.json(activeScanResponse)
      )
    );

    const { result } = renderHook(() => useActiveScan("scan-123"), {
      wrapper: createTestWrapper(),
    });

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(scan123);
  });

  it("returns undefined when scan is not found", async () => {
    server.use(
      http.get("/api/v2/scans/active", () =>
        HttpResponse.json(activeScanResponse)
      )
    );

    const { result } = renderHook(() => useActiveScan("nonexistent"), {
      wrapper: createTestWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeUndefined();
  });

  it("returns undefined when scanId is undefined", async () => {
    server.use(
      http.get("/api/v2/scans/active", () =>
        HttpResponse.json(activeScanResponse)
      )
    );

    const { result } = renderHook(() => useActiveScan(undefined), {
      wrapper: createTestWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeUndefined();
  });

  it("returns error when fetch fails", async () => {
    server.use(
      http.get("/api/v2/scans/active", () =>
        HttpResponse.text("Server Error", { status: 500 })
      )
    );

    const { result } = renderHook(() => useActiveScan("scan-123"), {
      wrapper: createTestWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeDefined();
    expect(result.current.error?.message).toContain("500");
  });
});
