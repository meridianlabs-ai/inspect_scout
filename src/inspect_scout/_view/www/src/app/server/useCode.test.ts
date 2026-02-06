// @vitest-environment jsdom
import { skipToken } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { Column } from "../../query/column";
import { server } from "../../test/setup-msw";
import { createTestWrapper } from "../../test/test-utils";

import { useCode } from "./useCode";

const simpleCondition = new Column("total_tokens").lt(75);

describe("useCode", () => {
  it("returns loading then data on successful fetch", async () => {
    const mockResponse = {
      python: "Not Yet Implemented",
      sqlite: '"total_tokens" < ?',
      duckdb: '"total_tokens" < ?',
      postgres: '"total_tokens" < $1',
    };

    server.use(
      http.post("/api/v2/code", () => HttpResponse.json(mockResponse))
    );

    const { result } = renderHook(() => useCode(simpleCondition), {
      wrapper: createTestWrapper(),
    });

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(mockResponse);
  });

  it("sends condition as request body", async () => {
    let capturedBody: unknown;

    server.use(
      http.post("/api/v2/code", async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json({ python: "test" });
      })
    );

    const { result } = renderHook(() => useCode(simpleCondition), {
      wrapper: createTestWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Condition is serialized via JSON.stringify, so compare as JSON
    expect(capturedBody).toEqual(JSON.parse(JSON.stringify(simpleCondition)));
  });

  it("returns error on server failure", async () => {
    server.use(
      http.post("/api/v2/code", () =>
        HttpResponse.text("Bad Request", { status: 400 })
      )
    );

    const { result } = renderHook(() => useCode(simpleCondition), {
      wrapper: createTestWrapper(),
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeDefined();
    expect(result.current.error?.message).toContain("400");
  });

  it("does not make request when skipToken is passed", async () => {
    let requestMade = false;

    server.use(
      http.post("/api/v2/code", () => {
        requestMade = true;
        return HttpResponse.json({});
      })
    );

    const { result } = renderHook(() => useCode(skipToken), {
      wrapper: createTestWrapper(),
    });

    // With skipToken, query stays pending and no request is made
    expect(result.current.loading).toBe(true);

    // Give it a tick to ensure no request fires
    await new Promise((r) => setTimeout(r, 50));
    expect(requestMade).toBe(false);
  });

  it("uses different cache entries for different conditions", async () => {
    let requestCount = 0;

    server.use(
      http.post("/api/v2/code", () => {
        requestCount++;
        return HttpResponse.json({ python: `response-${requestCount}` });
      })
    );

    const wrapper = createTestWrapper();

    const { result: result1 } = renderHook(
      () => useCode(new Column("a").eq(1)),
      { wrapper }
    );
    const { result: result2 } = renderHook(
      () => useCode(new Column("b").eq(2)),
      { wrapper }
    );

    await waitFor(() => {
      expect(result1.current.loading).toBe(false);
      expect(result2.current.loading).toBe(false);
    });

    // Two different conditions should trigger two separate requests
    expect(requestCount).toBe(2);
  });
});
