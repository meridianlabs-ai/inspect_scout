// @vitest-environment jsdom
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { Column } from "../../query/column";
import { server } from "../../test/setup-msw";
import { createTestWrapper } from "../../test/test-utils";
import type { TranscriptsResponse } from "../../types/api-types";
import { encodeBase64Url } from "../../utils/base64url";

import { useServerTranscripts } from "./useServerTranscripts";

const location = "/test/transcripts";
const encodedLocation = encodeBase64Url(location);
const endpoint = `/api/v2/transcripts/${encodedLocation}`;

const mockTranscriptsResponse: TranscriptsResponse = {
  items: [
    { transcript_id: "t-1", metadata: {} },
    { transcript_id: "t-2", metadata: {} },
  ],
  next_cursor: null,
  total_count: 2,
};

describe("useServerTranscripts", () => {
  it("returns transcripts on successful fetch", async () => {
    server.use(
      http.post(endpoint, () => HttpResponse.json(mockTranscriptsResponse))
    );

    const { result } = renderHook(() => useServerTranscripts(location), {
      wrapper: createTestWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(mockTranscriptsResponse);
  });

  it("sends sorting state as order_by in request body", async () => {
    let capturedBody: unknown;

    server.use(
      http.post(endpoint, async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json(mockTranscriptsResponse);
      })
    );

    const sorting = [
      { id: "date", desc: true },
      { id: "model", desc: false },
    ];

    const { result } = renderHook(
      () => useServerTranscripts(location, undefined, sorting),
      { wrapper: createTestWrapper() }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(capturedBody).toEqual({
      filter: null,
      order_by: [
        { column: "date", direction: "DESC" },
        { column: "model", direction: "ASC" },
      ],
      pagination: null,
    });
  });

  it("sends filter in request body", async () => {
    let capturedBody: unknown;

    server.use(
      http.post(endpoint, async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json(mockTranscriptsResponse);
      })
    );

    const filter = new Column("model").eq("gpt-4");

    const { result } = renderHook(
      () => useServerTranscripts(location, filter),
      { wrapper: createTestWrapper() }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(capturedBody).toMatchObject({
      filter: JSON.parse(JSON.stringify(filter)),
    });
  });

  it("returns error on server failure", async () => {
    server.use(
      http.post(endpoint, () =>
        HttpResponse.text("Server Error", { status: 500 })
      )
    );

    const { result } = renderHook(() => useServerTranscripts(location), {
      wrapper: createTestWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeDefined();
  });
});
