// @vitest-environment jsdom
import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { data, loading } from "../../utils/asyncData";

import { useActiveScan } from "./useActiveScan";
import { useScans } from "./useScans";

vi.mock("./useScans", () => ({
  useScans: vi.fn(),
}));

const mockUseScans = vi.mocked(useScans);

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
    mockUseScans.mockReturnValue(loading);

    const { result } = renderHook(() => useActiveScan("/scans", "scan-123"));

    expect(result.current).toBe(loading);
  });

  it("returns null when scan is not found", () => {
    mockUseScans.mockReturnValue(data([createMockScan("other-scan")] as never));

    const { result } = renderHook(() => useActiveScan("/scans", "scan-123"));

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeUndefined();
  });

  it("returns null when scan has no active_scan_info", () => {
    mockUseScans.mockReturnValue(
      data([createMockScan("scan-123", null)] as never)
    );

    const { result } = renderHook(() => useActiveScan("/scans", "scan-123"));

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeUndefined();
  });

  it("returns active_scan_info when scan is active", () => {
    const activeScanInfo = { scan_id: "scan-123", total_scans: 10 };
    mockUseScans.mockReturnValue(
      data([createMockScan("scan-123", activeScanInfo as never)] as never)
    );

    const { result } = renderHook(() => useActiveScan("/scans", "scan-123"));

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toEqual(activeScanInfo);
  });

  it("returns null when scanId is undefined", () => {
    mockUseScans.mockReturnValue(data([createMockScan("scan-123")] as never));

    const { result } = renderHook(() => useActiveScan("/scans", undefined));

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeUndefined();
  });

  it("returns error when scans fetch fails", () => {
    const error = new Error("Network error");
    mockUseScans.mockReturnValue({ loading: false, error });

    const { result } = renderHook(() => useActiveScan("/scans", "scan-123"));

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(error);
  });
});
