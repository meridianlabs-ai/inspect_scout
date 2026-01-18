// @vitest-environment jsdom
import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { data, loading } from "../../utils/asyncData";

import { useAdjacentTranscriptIds } from "./useAdjacentTranscriptIds";
import { useServerTranscriptsInfinite } from "./useServerTranscriptsInfinite";

vi.mock("./useServerTranscriptsInfinite", () => ({
  useServerTranscriptsInfinite: vi.fn(),
}));

const mockUseServerTranscriptsInfinite = vi.mocked(
  useServerTranscriptsInfinite
);

const createMockTranscript = (id: string) => ({
  transcript_id: id,
  source_uri: `/test/${id}`,
  task_id: "task-1",
  task_set: "set-1",
  model: "model-1",
  score: null,
  success: true,
  message_count: 10,
  total_time: 100,
  total_tokens: 500,
  date: "2024-01-01",
  error: null,
  metadata: {},
});

const createMockQueryResult = (
  pages: string[][],
  options: {
    isLoading?: boolean;
    error?: Error;
    hasNextPage?: boolean;
    isFetchingNextPage?: boolean;
  } = {}
) => ({
  data: options.isLoading
    ? undefined
    : {
        pages: pages.map((ids) => ({
          items: ids.map(createMockTranscript),
          next_cursor: null,
          total_count: ids.length,
        })),
        pageParams: pages.map(() => undefined),
      },
  error: options.error ?? null,
  isLoading: options.isLoading ?? false,
  hasNextPage: options.hasNextPage ?? false,
  isFetchingNextPage: options.isFetchingNextPage ?? false,
  fetchNextPage: vi.fn().mockResolvedValue(undefined),
  // Additional required fields from UseInfiniteQueryResult
  isFetching: false,
  isError: !!options.error,
  isSuccess: !options.isLoading && !options.error,
  status: options.isLoading ? "pending" : options.error ? "error" : "success",
  fetchStatus: "idle",
  refetch: vi.fn(),
  isFetchingPreviousPage: false,
  hasPreviousPage: false,
  fetchPreviousPage: vi.fn(),
  isRefetching: false,
  isPending: options.isLoading ?? false,
  isLoadingError: false,
  isRefetchError: false,
  dataUpdatedAt: Date.now(),
  errorUpdatedAt: 0,
  failureCount: 0,
  failureReason: null,
  errorUpdateCount: 0,
  isFetched: !options.isLoading,
  isPlaceholderData: false,
  isPaused: false,
  isStale: false,
});

describe("useAdjacentTranscriptIds", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns loading when query is loading", () => {
    mockUseServerTranscriptsInfinite.mockReturnValue(
      createMockQueryResult([[]], { isLoading: true }) as never
    );

    const { result } = renderHook(() =>
      useAdjacentTranscriptIds("id-1", "/location")
    );

    expect(result.current).toBe(loading);
  });

  it("returns [undefined, nextId] when id is at index 0", () => {
    mockUseServerTranscriptsInfinite.mockReturnValue(
      createMockQueryResult([["id-1", "id-2", "id-3"]]) as never
    );

    const { result } = renderHook(() =>
      useAdjacentTranscriptIds("id-1", "/location")
    );

    expect(result.current).toEqual(data([undefined, "id-2"]));
  });

  it("returns [prevId, nextId] when id is in middle of list", () => {
    mockUseServerTranscriptsInfinite.mockReturnValue(
      createMockQueryResult([["id-1", "id-2", "id-3"]]) as never
    );

    const { result } = renderHook(() =>
      useAdjacentTranscriptIds("id-2", "/location")
    );

    expect(result.current).toEqual(data(["id-1", "id-3"]));
  });

  it("returns [prevId, undefined] when id is last item and no more pages", () => {
    mockUseServerTranscriptsInfinite.mockReturnValue(
      createMockQueryResult([["id-1", "id-2", "id-3"]], {
        hasNextPage: false,
      }) as never
    );

    const { result } = renderHook(() =>
      useAdjacentTranscriptIds("id-3", "/location")
    );

    expect(result.current).toEqual(data(["id-2", undefined]));
  });

  it("calls fetchNextPage when id is last item and hasNextPage is true", () => {
    const mockFetchNextPage = vi.fn().mockResolvedValue(undefined);
    mockUseServerTranscriptsInfinite.mockReturnValue({
      ...createMockQueryResult([["id-1", "id-2", "id-3"]], {
        hasNextPage: true,
      }),
      fetchNextPage: mockFetchNextPage,
    } as never);

    renderHook(() => useAdjacentTranscriptIds("id-3", "/location"));

    expect(mockFetchNextPage).toHaveBeenCalled();
  });

  it("returns error when query has error", () => {
    const error = new Error("Network error");
    mockUseServerTranscriptsInfinite.mockReturnValue(
      createMockQueryResult([[]], { error }) as never
    );

    const { result } = renderHook(() =>
      useAdjacentTranscriptIds("id-1", "/location")
    );

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(error);
  });

  it("returns loading when id not found in loaded pages", () => {
    mockUseServerTranscriptsInfinite.mockReturnValue(
      createMockQueryResult([["id-1", "id-2", "id-3"]]) as never
    );

    const { result } = renderHook(() =>
      useAdjacentTranscriptIds("id-not-found", "/location")
    );

    expect(result.current).toBe(loading);
  });

  it("returns adjacent ids across page boundaries - next from next page", () => {
    mockUseServerTranscriptsInfinite.mockReturnValue(
      createMockQueryResult([
        ["id-1", "id-2"],
        ["id-3", "id-4"],
      ]) as never
    );

    const { result } = renderHook(() =>
      useAdjacentTranscriptIds("id-2", "/location")
    );

    expect(result.current).toEqual(data(["id-1", "id-3"]));
  });

  it("returns adjacent ids across page boundaries - prev from prev page", () => {
    mockUseServerTranscriptsInfinite.mockReturnValue(
      createMockQueryResult([
        ["id-1", "id-2"],
        ["id-3", "id-4"],
      ]) as never
    );

    const { result } = renderHook(() =>
      useAdjacentTranscriptIds("id-3", "/location")
    );

    expect(result.current).toEqual(data(["id-2", "id-4"]));
  });
});
