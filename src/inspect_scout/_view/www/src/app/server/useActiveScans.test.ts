// @vitest-environment jsdom
import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useApi } from "../../state/store";
import { data, loading } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

import { useActiveScans } from "./useActiveScans";

vi.mock("../../state/store", () => ({
  useApi: vi.fn(),
}));

vi.mock("../../utils/asyncDataFromQuery", () => ({
  useAsyncDataFromQuery: vi.fn(),
}));

const mockUseApi = vi.mocked(useApi);
const mockUseAsyncDataFromQuery = vi.mocked(useAsyncDataFromQuery);

describe("useServerActiveScans", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseApi.mockReturnValue({} as ReturnType<typeof useApi>);
  });

  it("returns loading state when query is pending", () => {
    mockUseAsyncDataFromQuery.mockReturnValue(loading);

    const { result } = renderHook(() => useActiveScans());

    expect(result.current).toEqual(loading);
  });

  it("returns data on successful fetch", () => {
    const mockActiveScans = {
      "scan-123": {
        scan_id: "scan-123",
        metrics: {
          process_count: 2,
          task_count: 4,
          completed_scans: 100,
        },
        last_updated: 1704067200,
      },
    };

    mockUseAsyncDataFromQuery.mockReturnValue(data(mockActiveScans));

    const { result } = renderHook(() => useActiveScans());

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toEqual(mockActiveScans);
  });

  it("returns empty object when no active scans", () => {
    mockUseAsyncDataFromQuery.mockReturnValue(data({}));

    const { result } = renderHook(() => useActiveScans());

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toEqual({});
  });

  it("returns error on fetch failure", () => {
    const error = new Error("Network error");
    mockUseAsyncDataFromQuery.mockReturnValue({ loading: false, error });

    const { result } = renderHook(() => useActiveScans());

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(error);
  });

  it("passes correct options to useAsyncDataFromQuery", () => {
    const mockApi = {
      getActiveScans: vi.fn(),
    };
    mockUseApi.mockReturnValue(mockApi as unknown as ReturnType<typeof useApi>);
    mockUseAsyncDataFromQuery.mockReturnValue(loading);

    renderHook(() => useActiveScans());

    expect(mockUseAsyncDataFromQuery).toHaveBeenCalledWith({
      queryKey: ["active-scans"],
      queryFn: expect.any(Function),
      refetchInterval: 5000,
    });
  });

  it("queryFn extracts items from API response", async () => {
    const mockItems = { "scan-1": { scan_id: "scan-1" } };
    const mockApi = {
      getActiveScans: vi.fn().mockResolvedValue({ items: mockItems }),
    };
    mockUseApi.mockReturnValue(mockApi as unknown as ReturnType<typeof useApi>);
    mockUseAsyncDataFromQuery.mockReturnValue(loading);

    renderHook(() => useActiveScans());

    const callArgs = mockUseAsyncDataFromQuery.mock.calls[0]?.[0];
    expect(callArgs).toBeDefined();
    const queryFn = callArgs!.queryFn as () => Promise<unknown>;
    const result = await queryFn();

    expect(mockApi.getActiveScans).toHaveBeenCalled();
    expect(result).toEqual(mockItems);
  });
});
