// @vitest-environment jsdom
import { skipToken } from "@tanstack/react-query";
import { renderHook, waitFor, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "../../test/setup-msw";
import { createTestWrapper } from "../../test/test-utils";
import { encodeBase64Url } from "../../utils/base64url";

import {
  useBulkDeleteValidationCases,
  useUpdateValidationCase,
  useValidationCase,
} from "./useValidations";

const uri = "file:///validations/test.json";
const caseId = "case-1";
const encodedUri = encodeBase64Url(uri);
const encodedCaseId = encodeBase64Url(caseId);

const mockCase = {
  id: caseId,
  labels: { correct: true },
  target: "expected answer",
  predicate: null,
  split: null,
};

describe("useValidationCase", () => {
  it("returns validation case on success", async () => {
    server.use(
      http.get(`/api/v2/validations/${encodedUri}/${encodedCaseId}`, () =>
        HttpResponse.json(mockCase)
      )
    );

    const { result } = renderHook(
      () => useValidationCase({ url: uri, caseId }),
      { wrapper: createTestWrapper() }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(mockCase);
  });

  it("returns null instead of error on 404", async () => {
    server.use(
      http.get(`/api/v2/validations/${encodedUri}/${encodedCaseId}`, () =>
        HttpResponse.text("Not Found", { status: 404 })
      )
    );

    const { result } = renderHook(
      () => useValidationCase({ url: uri, caseId }),
      { wrapper: createTestWrapper() }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeUndefined();
  });

  it("returns error on non-404 failures", async () => {
    server.use(
      http.get(`/api/v2/validations/${encodedUri}/${encodedCaseId}`, () =>
        HttpResponse.text("Server Error", { status: 500 })
      )
    );

    const { result } = renderHook(
      () => useValidationCase({ url: uri, caseId }),
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
      http.get(`/api/v2/validations/${encodedUri}/${encodedCaseId}`, () => {
        requestMade = true;
        return HttpResponse.json(mockCase);
      })
    );

    const { result } = renderHook(() => useValidationCase(skipToken), {
      wrapper: createTestWrapper(),
    });

    expect(result.current.loading).toBe(true);

    await new Promise((r) => setTimeout(r, 50));
    expect(requestMade).toBe(false);
  });
});

describe("useUpdateValidationCase", () => {
  it("sends update and returns updated case", async () => {
    let capturedBody: unknown;

    const updatedCase = { ...mockCase, labels: { correct: false } };

    server.use(
      http.post(
        `/api/v2/validations/${encodedUri}/${encodedCaseId}`,
        async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json(updatedCase);
        }
      )
    );

    const { result } = renderHook(() => useUpdateValidationCase(uri), {
      wrapper: createTestWrapper(),
    });

    const updateData = { labels: { correct: false } };

    await act(() => result.current.mutateAsync({ caseId, data: updateData }));

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(capturedBody).toEqual(updateData);
    expect(result.current.data).toEqual(updatedCase);
  });

  it("rolls back optimistic update on error", async () => {
    const wrapper = createTestWrapper();

    // Pre-populate the case cache
    server.use(
      http.get(`/api/v2/validations/${encodedUri}/${encodedCaseId}`, () =>
        HttpResponse.json(mockCase)
      )
    );

    const { result: caseResult } = renderHook(
      () => useValidationCase({ url: uri, caseId }),
      { wrapper }
    );

    await waitFor(() => {
      expect(caseResult.current.loading).toBe(false);
    });

    expect(caseResult.current.data).toEqual(mockCase);

    // Now set up the update to fail
    server.use(
      http.post(`/api/v2/validations/${encodedUri}/${encodedCaseId}`, () =>
        HttpResponse.text("Server Error", { status: 500 })
      )
    );

    const { result: mutationResult } = renderHook(
      () => useUpdateValidationCase(uri),
      { wrapper }
    );

    await act(async () => {
      try {
        await mutationResult.current.mutateAsync({
          caseId,
          data: { labels: { correct: false } },
        });
      } catch {
        // expected
      }
    });

    await waitFor(() => {
      expect(mutationResult.current.isError).toBe(true);
    });

    // After rollback, the cache should have the original data
    await waitFor(() => {
      expect(caseResult.current.data).toEqual(mockCase);
    });
  });
});

describe("useBulkDeleteValidationCases", () => {
  const caseIds = ["case-1", "case-2", "case-3"];

  const deleteEndpoint = (id: string) =>
    `/api/v2/validations/${encodedUri}/${encodeBase64Url(id)}`;

  it("deletes all cases successfully", async () => {
    for (const id of caseIds) {
      server.use(
        http.delete(deleteEndpoint(id), () =>
          HttpResponse.json({ deleted: true })
        )
      );
    }

    const { result } = renderHook(() => useBulkDeleteValidationCases(uri), {
      wrapper: createTestWrapper(),
    });

    await act(() => result.current.mutateAsync(caseIds));

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual({ succeeded: 3, failed: 0 });
  });

  it("handles partial failures gracefully", async () => {
    // case-1 and case-3 succeed, case-2 fails
    server.use(
      http.delete(deleteEndpoint("case-1"), () =>
        HttpResponse.json({ deleted: true })
      ),
      http.delete(deleteEndpoint("case-2"), () =>
        HttpResponse.text("Server Error", { status: 500 })
      ),
      http.delete(deleteEndpoint("case-3"), () =>
        HttpResponse.json({ deleted: true })
      )
    );

    const { result } = renderHook(() => useBulkDeleteValidationCases(uri), {
      wrapper: createTestWrapper(),
    });

    await act(() => result.current.mutateAsync(caseIds));

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual({ succeeded: 2, failed: 1 });
  });

  it("throws when all deletions fail", async () => {
    for (const id of caseIds) {
      server.use(
        http.delete(deleteEndpoint(id), () =>
          HttpResponse.text("Server Error", { status: 500 })
        )
      );
    }

    const { result } = renderHook(() => useBulkDeleteValidationCases(uri), {
      wrapper: createTestWrapper(),
    });

    await act(async () => {
      try {
        await result.current.mutateAsync(caseIds);
      } catch {
        // expected
      }
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toContain("All deletions failed");
  });
});
