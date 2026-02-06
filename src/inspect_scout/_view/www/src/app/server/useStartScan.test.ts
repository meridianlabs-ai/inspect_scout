// @vitest-environment jsdom
import { renderHook, waitFor, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "../../test/setup-msw";
import { createTestWrapper } from "../../test/test-utils";
import type { ScanJobConfig, Status } from "../../types/api-types";

import { useStartScan } from "./useStartScan";

const mockScanConfig: ScanJobConfig = {
  filter: ["task_id = 'test'"],
};

const mockStatus: Status = {
  complete: false,
  errors: [],
  location: "/scans/test",
  spec: {
    scan_id: "test-scan-id",
    scan_name: "test-scan",
    options: { max_transcripts: 25 },
    packages: {},
    scanners: {},
    timestamp: "2024-01-01T00:00:00Z",
  },
  summary: { complete: false, scanners: {} },
};

describe("useStartScan", () => {
  it("sends scan config and returns status on success", async () => {
    let capturedBody: unknown;

    server.use(
      http.post("/api/v2/startscan", async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json<Status>(mockStatus);
      })
    );

    const { result } = renderHook(() => useStartScan(), {
      wrapper: createTestWrapper(),
    });

    await act(() => result.current.mutateAsync(mockScanConfig));

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(capturedBody).toEqual(mockScanConfig);
    expect(result.current.data).toEqual(mockStatus);
  });

  it("sets error state on server failure", async () => {
    server.use(
      http.post("/api/v2/startscan", () =>
        HttpResponse.text("Bad config", { status: 400 })
      )
    );

    const { result } = renderHook(() => useStartScan(), {
      wrapper: createTestWrapper(),
    });

    await act(async () => {
      try {
        await result.current.mutateAsync(mockScanConfig);
      } catch {
        // expected
      }
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toContain("400");
  });
});
