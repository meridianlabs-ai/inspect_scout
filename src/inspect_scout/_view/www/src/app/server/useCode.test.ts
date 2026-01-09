// @vitest-environment jsdom
import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Column } from "../../query/column";
import { useApi } from "../../state/store";
import { data, loading } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

import { useCode } from "./useCode";

vi.mock("../../state/store", () => ({
  useApi: vi.fn(),
}));

vi.mock("../../utils/asyncDataFromQuery", () => ({
  useAsyncDataFromQuery: vi.fn(),
}));

const mockUseApi = vi.mocked(useApi);
const mockUseAsyncDataFromQuery = vi.mocked(useAsyncDataFromQuery);

const simpleCondition = new Column("total_tokens").lt(75);

describe("useCode", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseApi.mockReturnValue({} as ReturnType<typeof useApi>);
  });

  it("returns loading state when query is pending", () => {
    mockUseAsyncDataFromQuery.mockReturnValue(loading);

    const { result } = renderHook(() => useCode(simpleCondition));

    expect(result.current).toEqual(loading);
  });

  it("returns data on successful fetch", () => {
    const mockCodeResponse = {
      python: "Not Yet Implemented",
      sqlite: '"total_tokens" < ?',
      duckdb: '"total_tokens" < ?',
      postgres: '"total_tokens" < $1',
    };

    mockUseAsyncDataFromQuery.mockReturnValue(data(mockCodeResponse));

    const { result } = renderHook(() => useCode(simpleCondition));

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toEqual(mockCodeResponse);
  });

  it("returns error on fetch failure", () => {
    const error = new Error("Network error");
    mockUseAsyncDataFromQuery.mockReturnValue({ loading: false, error });

    const { result } = renderHook(() => useCode(simpleCondition));

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(error);
  });

  it("passes correct options to useAsyncDataFromQuery", () => {
    const mockApi = {
      postCode: vi.fn(),
    };
    mockUseApi.mockReturnValue(mockApi as unknown as ReturnType<typeof useApi>);
    mockUseAsyncDataFromQuery.mockReturnValue(loading);

    renderHook(() => useCode(simpleCondition));

    expect(mockUseAsyncDataFromQuery).toHaveBeenCalledWith({
      queryKey: ["code", simpleCondition],
      queryFn: expect.any(Function),
    });
  });

  it("queryFn calls postCode with condition", async () => {
    const mockResponse = { python: "test", sqlite: "test" };
    const mockApi = {
      postCode: vi.fn().mockResolvedValue(mockResponse),
    };
    mockUseApi.mockReturnValue(mockApi as unknown as ReturnType<typeof useApi>);
    mockUseAsyncDataFromQuery.mockReturnValue(loading);

    renderHook(() => useCode(simpleCondition));

    const callArgs = mockUseAsyncDataFromQuery.mock.calls[0]?.[0];
    expect(callArgs).toBeDefined();
    const queryFn = callArgs!.queryFn as () => Promise<unknown>;
    const result = await queryFn();

    expect(mockApi.postCode).toHaveBeenCalledWith(simpleCondition);
    expect(result).toEqual(mockResponse);
  });

  it("uses condition in queryKey for caching", () => {
    const condition1 = new Column("a").eq(1);
    const condition2 = new Column("b").eq(2);

    mockUseAsyncDataFromQuery.mockReturnValue(loading);

    renderHook(() => useCode(condition1));
    renderHook(() => useCode(condition2));

    const call1 = mockUseAsyncDataFromQuery.mock.calls[0]?.[0];
    const call2 = mockUseAsyncDataFromQuery.mock.calls[1]?.[0];

    expect(call1?.queryKey).toEqual(["code", condition1]);
    expect(call2?.queryKey).toEqual(["code", condition2]);
  });
});
