// @vitest-environment jsdom
import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Column } from "../../query/column";
import { useApi } from "../../state/store";
import { data, loading } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

import { useTranscriptColumnValues } from "./useServerTranscriptColumnValues";

vi.mock("../../state/store", () => ({
  useApi: vi.fn(),
}));

vi.mock("../../utils/asyncDataFromQuery", () => ({
  useAsyncDataFromQuery: vi.fn(),
}));

const mockUseApi = vi.mocked(useApi);
const mockUseAsyncDataFromQuery = vi.mocked(useAsyncDataFromQuery);

describe("useServerTranscriptColumnValues", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseApi.mockReturnValue({} as ReturnType<typeof useApi>);
  });

  it("returns loading state when query is pending", () => {
    mockUseAsyncDataFromQuery.mockReturnValue(loading);

    const { result } = renderHook(() =>
      useTranscriptColumnValues("/transcripts", "model")
    );

    expect(result.current).toEqual(loading);
  });

  it("returns data on successful fetch", () => {
    const mockValues = ["gpt-4", "claude-3", "gemini"];
    mockUseAsyncDataFromQuery.mockReturnValue(data(mockValues));

    const { result } = renderHook(() =>
      useTranscriptColumnValues("/transcripts", "model")
    );

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toEqual(mockValues);
  });

  it("returns error on fetch failure", () => {
    const error = new Error("Network error");
    mockUseAsyncDataFromQuery.mockReturnValue({ loading: false, error });

    const { result } = renderHook(() =>
      useTranscriptColumnValues("/transcripts", "model")
    );

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(error);
  });

  it("passes correct options to useAsyncDataFromQuery", () => {
    const mockApi = {
      getTranscriptColumnValues: vi.fn(),
    };
    mockUseApi.mockReturnValue(mockApi as unknown as ReturnType<typeof useApi>);
    mockUseAsyncDataFromQuery.mockReturnValue(loading);

    renderHook(() => useTranscriptColumnValues("/transcripts", "model"));

    expect(mockUseAsyncDataFromQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: [
          "transcriptColumnValues",
          "/transcripts",
          "model",
          undefined,
        ],
        queryFn: expect.any(Function),
        staleTime: 10 * 60 * 1000,
      })
    );
  });

  it("includes filter in queryKey when provided", () => {
    const filter = new Column("score").gt(0.5);
    mockUseAsyncDataFromQuery.mockReturnValue(loading);

    renderHook(() =>
      useTranscriptColumnValues("/transcripts", "model", filter)
    );

    expect(mockUseAsyncDataFromQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ["transcriptColumnValues", "/transcripts", "model", filter],
      })
    );
  });

  it("queryFn calls getTranscriptColumnValues with correct args", async () => {
    const mockValues = ["value1", "value2"];
    const mockApi = {
      getTranscriptColumnValues: vi.fn().mockResolvedValue(mockValues),
    };
    mockUseApi.mockReturnValue(mockApi as unknown as ReturnType<typeof useApi>);
    mockUseAsyncDataFromQuery.mockReturnValue(loading);

    const filter = new Column("score").gt(0.5);
    renderHook(() =>
      useTranscriptColumnValues("/transcripts", "model", filter)
    );

    const callArgs = mockUseAsyncDataFromQuery.mock.calls[0]?.[0];
    expect(callArgs).toBeDefined();
    const queryFn = callArgs!.queryFn as () => Promise<unknown>;
    const result = await queryFn();

    expect(mockApi.getTranscriptColumnValues).toHaveBeenCalledWith(
      "/transcripts",
      "model",
      filter
    );
    expect(result).toEqual(mockValues);
  });
});
