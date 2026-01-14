// @vitest-environment jsdom
import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useApi } from "../../state/store";
import { data, loading } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

import { useTranscriptsColumnValues } from "./useTranscriptsColumnValues";

vi.mock("../../state/store", () => ({
  useApi: vi.fn(),
}));

vi.mock("../../utils/asyncDataFromQuery", () => ({
  useAsyncDataFromQuery: vi.fn(),
}));

const mockUseApi = vi.mocked(useApi);
const mockUseAsyncDataFromQuery = vi.mocked(useAsyncDataFromQuery);

describe("useTranscriptsColumnValues", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseApi.mockReturnValue({} as ReturnType<typeof useApi>);
  });

  it("returns loading state when query is pending", () => {
    mockUseAsyncDataFromQuery.mockReturnValue(loading);

    const { result } = renderHook(() =>
      useTranscriptsColumnValues("/transcripts", "model", undefined)
    );

    expect(result.current).toEqual(loading);
  });

  it("returns data on successful fetch", () => {
    const mockValues = ["gpt-4", "claude-3", "gemini"];
    mockUseAsyncDataFromQuery.mockReturnValue(data(mockValues));

    const { result } = renderHook(() =>
      useTranscriptsColumnValues("/transcripts", "model", undefined)
    );

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toEqual(mockValues);
  });

  it("returns error on fetch failure", () => {
    const error = new Error("Network error");
    mockUseAsyncDataFromQuery.mockReturnValue({ loading: false, error });

    const { result } = renderHook(() =>
      useTranscriptsColumnValues("/transcripts", "model", undefined)
    );

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(error);
  });
});
