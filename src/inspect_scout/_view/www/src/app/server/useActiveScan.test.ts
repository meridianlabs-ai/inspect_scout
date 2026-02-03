// @vitest-environment jsdom
import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ActiveScanInfo } from "../../types/api-types";
import { data, loading } from "../../utils/asyncData";

import { useActiveScan } from "./useActiveScan";
import { useActiveScans } from "./useActiveScans";

vi.mock("./useActiveScans", () => ({
  useActiveScans: vi.fn(),
}));

const mockUseActiveScans = vi.mocked(useActiveScans);

const createMockActiveScanInfo = (scanId: string): ActiveScanInfo =>
  ({
    scan_id: scanId,
    total_scans: 10,
    metrics: { completed_scans: 5 },
  }) as ActiveScanInfo;

describe("useActiveScan", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns loading state when active scans are loading", () => {
    mockUseActiveScans.mockReturnValue(loading);

    const { result } = renderHook(() => useActiveScan("scan-123"));

    expect(result.current).toBe(loading);
  });

  it("returns undefined when scan is not found in active scans", () => {
    mockUseActiveScans.mockReturnValue(
      data({ "other-scan": createMockActiveScanInfo("other-scan") })
    );

    const { result } = renderHook(() => useActiveScan("scan-123"));

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeUndefined();
  });

  it("returns ActiveScanInfo when scan is active", () => {
    const activeScanInfo = createMockActiveScanInfo("scan-123");
    mockUseActiveScans.mockReturnValue(data({ "scan-123": activeScanInfo }));

    const { result } = renderHook(() => useActiveScan("scan-123"));

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toEqual(activeScanInfo);
  });

  it("returns undefined when scanId is undefined", () => {
    mockUseActiveScans.mockReturnValue(
      data({ "scan-123": createMockActiveScanInfo("scan-123") })
    );

    const { result } = renderHook(() => useActiveScan(undefined));

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeUndefined();
  });

  it("returns error when active scans fetch fails", () => {
    const error = new Error("Network error");
    mockUseActiveScans.mockReturnValue({ loading: false, error });

    const { result } = renderHook(() => useActiveScan("scan-123"));

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(error);
  });
});
