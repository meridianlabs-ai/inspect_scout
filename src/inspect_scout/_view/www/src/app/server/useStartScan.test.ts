// @vitest-environment jsdom
import { renderHook, waitFor, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "../../test/setup-msw";
import { createTestWrapper } from "../../test/test-utils";

import { useStartScan } from "./useStartScan";

const mockScanConfig = {
  filter: ["task_id = 'test'"],
};

const mockStatus = {
  complete: false,
  errors: [],
  location: "/scans/test",
  spec: { scanners: [] },
  summary: { total: 0, completed: 0 },
};

describe("useStartScan", () => {
  it("sends scan config and returns status on success", async () => {
    let capturedBody: unknown;

    server.use(
      http.post("/api/v2/startscan", async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json(mockStatus);
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
