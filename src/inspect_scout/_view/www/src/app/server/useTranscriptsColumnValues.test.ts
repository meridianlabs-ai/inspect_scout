// @vitest-environment jsdom
import { skipToken } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "../../test/setup-msw";
import { createTestWrapper } from "../../test/test-utils";
import { encodeBase64Url } from "../../utils/base64url";

import { useTranscriptsColumnValues } from "./useTranscriptsColumnValues";

const location = "/transcripts";
const encodedLocation = encodeBase64Url(location);

describe("useTranscriptsColumnValues", () => {
  it("returns loading then data on successful fetch", async () => {
    const mockValues = ["gpt-4", "claude-3", "gemini"];

    server.use(
      http.post(`/api/v2/transcripts/${encodedLocation}/distinct`, () =>
        HttpResponse.json(mockValues)
      )
    );

    const { result } = renderHook(
      () =>
        useTranscriptsColumnValues({
          location,
          column: "model",
          filter: undefined,
        }),
      { wrapper: createTestWrapper() }
    );

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(mockValues);
  });

  it("sends column and filter in request body", async () => {
    let capturedBody: unknown;

    server.use(
      http.post(
        `/api/v2/transcripts/${encodedLocation}/distinct`,
        async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json([]);
        }
      )
    );

    const { result } = renderHook(
      () =>
        useTranscriptsColumnValues({
          location,
          column: "model",
          filter: undefined,
        }),
      { wrapper: createTestWrapper() }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(capturedBody).toEqual({ column: "model", filter: null });
  });

  it("returns error on server failure", async () => {
    server.use(
      http.post(`/api/v2/transcripts/${encodedLocation}/distinct`, () =>
        HttpResponse.text("Server Error", { status: 500 })
      )
    );

    const { result } = renderHook(
      () =>
        useTranscriptsColumnValues({
          location,
          column: "model",
          filter: undefined,
        }),
      { wrapper: createTestWrapper() }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeDefined();
    expect(result.current.error?.message).toContain("500");
  });

  it("does not make request when skipToken is passed", async () => {
    let requestMade = false;

    server.use(
      http.post(`/api/v2/transcripts/${encodedLocation}/distinct`, () => {
        requestMade = true;
        return HttpResponse.json([]);
      })
    );

    const { result } = renderHook(() => useTranscriptsColumnValues(skipToken), {
      wrapper: createTestWrapper(),
    });

    expect(result.current.loading).toBe(true);

    await new Promise((r) => setTimeout(r, 50));
    expect(requestMade).toBe(false);
  });
});
