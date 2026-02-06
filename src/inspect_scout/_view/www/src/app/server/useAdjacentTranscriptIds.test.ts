// @vitest-environment jsdom
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "../../test/setup-msw";
import { createTestWrapper } from "../../test/test-utils";
import type {
  TranscriptInfo,
  TranscriptsResponse,
} from "../../types/api-types";
import { encodeBase64Url } from "../../utils/base64url";

import { useAdjacentTranscriptIds } from "./useAdjacentTranscriptIds";

const location = "/test-transcripts";
const encodedLocation = encodeBase64Url(location);
const endpoint = `/api/v2/transcripts/${encodedLocation}`;

const makeTranscript = (id: string): TranscriptInfo => ({
  transcript_id: id,
  metadata: {},
});

type CursorObject = { page: string } | null;

type PaginationBody = {
  filter: unknown;
  order_by: unknown;
  pagination: { cursor: CursorObject } | null;
};

/**
 * Creates an MSW handler that returns paginated transcript responses.
 * Each entry in `pages` maps a cursor key to a page of transcript IDs.
 * The first entry (cursor `null`) is the initial page.
 */
const handlePaginatedTranscripts = (
  pages: Map<string | null, { ids: string[]; nextCursor: string | null }>
) =>
  http.post(endpoint, async ({ request }) => {
    const body = (await request.json()) as PaginationBody;
    const cursorObj = body.pagination?.cursor ?? null;
    const cursorKey = cursorObj?.page ?? null;
    const page = pages.get(cursorKey);
    if (!page) {
      return HttpResponse.json<TranscriptsResponse>({
        items: [],
        next_cursor: null,
        total_count: 0,
      });
    }
    return HttpResponse.json<TranscriptsResponse>({
      items: page.ids.map(makeTranscript),
      next_cursor: page.nextCursor ? { page: page.nextCursor } : null,
      total_count: page.ids.length,
    });
  });

describe("useAdjacentTranscriptIds", () => {
  it("returns [undefined, nextId] for the first item", async () => {
    server.use(
      handlePaginatedTranscripts(
        new Map([[null, { ids: ["id-1", "id-2", "id-3"], nextCursor: null }]])
      )
    );

    const { result } = renderHook(
      () => useAdjacentTranscriptIds("id-1", location),
      { wrapper: createTestWrapper() }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual([undefined, "id-2"]);
  });

  it("returns [prevId, nextId] for a middle item", async () => {
    server.use(
      handlePaginatedTranscripts(
        new Map([[null, { ids: ["id-1", "id-2", "id-3"], nextCursor: null }]])
      )
    );

    const { result } = renderHook(
      () => useAdjacentTranscriptIds("id-2", location),
      { wrapper: createTestWrapper() }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(["id-1", "id-3"]);
  });

  it("returns [prevId, undefined] for the last item with no more pages", async () => {
    server.use(
      handlePaginatedTranscripts(
        new Map([[null, { ids: ["id-1", "id-2", "id-3"], nextCursor: null }]])
      )
    );

    const { result } = renderHook(
      () => useAdjacentTranscriptIds("id-3", location),
      { wrapper: createTestWrapper() }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(["id-2", undefined]);
  });

  it("fetches next page when viewing last item with more pages available", async () => {
    server.use(
      handlePaginatedTranscripts(
        new Map([
          [null, { ids: ["id-1", "id-2"], nextCursor: "cursor-2" }],
          ["cursor-2", { ids: ["id-3", "id-4"], nextCursor: null }],
        ])
      )
    );

    const { result } = renderHook(
      () => useAdjacentTranscriptIds("id-2", location),
      { wrapper: createTestWrapper() }
    );

    // Initially loads first page, id-2 is last item so it triggers fetchNextPage
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // After second page loads, id-3 becomes the next adjacent ID
    await waitFor(() => {
      expect(result.current.data).toEqual(["id-1", "id-3"]);
    });
  });

  it("returns adjacent ids across page boundaries", async () => {
    const wrapper = createTestWrapper();

    server.use(
      handlePaginatedTranscripts(
        new Map([
          [null, { ids: ["id-1", "id-2"], nextCursor: "cursor-2" }],
          ["cursor-2", { ids: ["id-3", "id-4"], nextCursor: null }],
        ])
      )
    );

    // First, view id-2 (last item on page 1) — this triggers fetchNextPage
    const { result: result1 } = renderHook(
      () => useAdjacentTranscriptIds("id-2", location, 2),
      { wrapper }
    );

    // Wait for both pages to load (id-2 triggers page 2 fetch)
    await waitFor(() => {
      expect(result1.current.loading).toBe(false);
      expect(result1.current.data).toEqual(["id-1", "id-3"]);
    });

    // Now view id-3 (first item on page 2) — both pages are cached
    const { result: result2 } = renderHook(
      () => useAdjacentTranscriptIds("id-3", location, 2),
      { wrapper }
    );

    await waitFor(() => {
      expect(result2.current.loading).toBe(false);
    });

    // id-2 is last on prev page, id-4 is next on same page
    expect(result2.current.data).toEqual(["id-2", "id-4"]);
  });

  it("returns error when fetch fails", async () => {
    server.use(
      http.post(endpoint, () =>
        HttpResponse.text("Server Error", { status: 500 })
      )
    );

    const { result } = renderHook(
      () => useAdjacentTranscriptIds("id-1", location),
      { wrapper: createTestWrapper() }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeDefined();
    expect(result.current.error?.message).toContain("500");
  });

  it("returns loading when location is null", async () => {
    const { result } = renderHook(
      () => useAdjacentTranscriptIds("id-1", null),
      { wrapper: createTestWrapper() }
    );

    // No fetch should be made — skipToken path
    expect(result.current.loading).toBe(true);

    await new Promise((r) => setTimeout(r, 50));
    expect(result.current.loading).toBe(true);
  });
});
