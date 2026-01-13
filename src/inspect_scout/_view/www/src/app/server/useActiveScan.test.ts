// @vitest-environment jsdom
import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { data, loading } from "../../utils/asyncData";

import { useActiveScan } from "./useActiveScan";
import { useServerScans } from "./useServerScans";

vi.mock("./useServerScans", () => ({
  useServerScans: vi.fn(),
}));

const mockUseServerScans = vi.mocked(useServerScans);

const createMockScan = (
  scanId: string,
  activeScanInfo: { scan_id: string } | null = null
) => ({
  spec: { scan_id: scanId },
  active_scan_info: activeScanInfo,
  complete: true,
  errors: [],
  location: "/test",
  summary: {},
});

describe("useActiveScan", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns loading state when scans are loading", () => {
    mockUseServerScans.mockReturnValue(loading);

    const { result } = renderHook(() => useActiveScan("scan-123"));

    expect(result.current).toBe(loading);
  });

  it("returns null when scan is not found", () => {
    mockUseServerScans.mockReturnValue(
      data([createMockScan("other-scan")] as never)
    );

    const { result } = renderHook(() => useActiveScan("scan-123"));

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeUndefined();
  });

  it("returns null when scan has no active_scan_info", () => {
    mockUseServerScans.mockReturnValue(
      data([createMockScan("scan-123", null)] as never)
    );

    const { result } = renderHook(() => useActiveScan("scan-123"));

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeUndefined();
  });

  it("returns active_scan_info when scan is active", () => {
    const activeScanInfo = { scan_id: "scan-123", total_scans: 10 };
    mockUseServerScans.mockReturnValue(
      data([createMockScan("scan-123", activeScanInfo as never)] as never)
    );

    const { result } = renderHook(() => useActiveScan("scan-123"));

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toEqual(activeScanInfo);
  });

  it("returns null when scanId is undefined", () => {
    mockUseServerScans.mockReturnValue(
      data([createMockScan("scan-123")] as never)
    );

    const { result } = renderHook(() => useActiveScan(undefined));

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeUndefined();
  });

  it("returns error when scans fetch fails", () => {
    const error = new Error("Network error");
    mockUseServerScans.mockReturnValue({ loading: false, error });

    const { result } = renderHook(() => useActiveScan("scan-123"));

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(error);
  });
});
