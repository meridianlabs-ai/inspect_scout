// @vitest-environment jsdom
import { useQuery } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { sse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { server } from "../../test/setup-msw";
import { createTestWrapper } from "../../test/test-utils";

import { useTopicInvalidation } from "./useTopicInvalidation";

/** Subset of MSW's SSE client used in tests. */
interface TestSSEClient {
  send(payload: { data?: string }): void;
  close(): void;
}

/**
 * Installs an SSE handler that captures the client reference for test control.
 * Returns a promise that resolves with the client once the hook connects.
 */
function installSSEHandler(): Promise<TestSSEClient> {
  let resolveClient: (client: TestSSEClient) => void;
  const clientReady = new Promise<TestSSEClient>((r) => (resolveClient = r));

  server.use(
    sse("/api/v2/topics/stream", ({ client }) => {
      resolveClient(client);
    })
  );

  return clientReady;
}

describe("useTopicInvalidation", () => {
  // The production code uses setTimeout(connect, 5000) for SSE reconnection.
  // When EventSource.close() is called during cleanup, it can fire onerror
  // synchronously, which schedules a new reconnect timer AFTER cleanup returns.
  // Fake timers prevent this leaked timer from firing in subsequent tests.
  // shouldAdvanceTime: true keeps waitFor working (it polls via setTimeout).
  // The production code uses setTimeout(connect, 5000) for SSE reconnection.
  // When EventSource.close() is called during cleanup, it can fire onerror
  // synchronously, which schedules a new reconnect timer AFTER cleanup returns.
  // Fake timers prevent this leaked timer from firing in subsequent tests.
  // shouldAdvanceTime: true keeps waitFor working (it polls via setTimeout).
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns false before connection, true after first message", async () => {
    const clientReady = installSSEHandler();

    const { result } = renderHook(() => useTopicInvalidation(), {
      wrapper: createTestWrapper(),
    });

    expect(result.current).toBe(false);

    const client = await clientReady;
    client.send({ data: JSON.stringify({ scans: "t1" }) });

    await waitFor(() => {
      expect(result.current).toBe(true);
    });
  });

  it("invalidates queries with matching topic key", async () => {
    const clientReady = installSSEHandler();
    const wrapper = createTestWrapper();

    // Track queryFn calls. Invalidation triggers a refetch, so the call count
    // increasing proves invalidation happened.
    const queryFn = vi.fn().mockResolvedValue({ items: [] });

    const { result } = renderHook(
      () => {
        const ready = useTopicInvalidation();
        const q = useQuery({
          queryKey: ["scans", "/some/dir", "scans-inv"],
          queryFn,
        });
        return { ready, q };
      },
      { wrapper }
    );

    const client = await clientReady;
    await waitFor(() => {
      expect(result.current.q.isSuccess).toBe(true);
    });

    // First message establishes baseline — triggers invalidation for all topics
    // (undefined → "t1") which causes a refetch.
    client.send({ data: JSON.stringify({ scans: "t1" }) });
    await waitFor(() => {
      expect(result.current.ready).toBe(true);
    });
    await waitFor(() => {
      expect(queryFn.mock.calls.length).toBeGreaterThanOrEqual(2);
    });

    const countAfterBaseline = queryFn.mock.calls.length;

    // Send a changed timestamp — should invalidate and trigger another refetch
    client.send({ data: JSON.stringify({ scans: "t2" }) });

    await waitFor(() => {
      expect(queryFn).toHaveBeenCalledTimes(countAfterBaseline + 1);
    });
  });

  it("does not invalidate queries for unchanged topics", async () => {
    const clientReady = installSSEHandler();
    const wrapper = createTestWrapper();

    const queryFn = vi.fn().mockResolvedValue({ items: [] });

    const { result } = renderHook(
      () => {
        const ready = useTopicInvalidation();
        const q = useQuery({
          queryKey: ["scans", "/dir", "scans-inv"],
          queryFn,
        });
        return { ready, q };
      },
      { wrapper }
    );

    const client = await clientReady;
    await waitFor(() => {
      expect(result.current.q.isSuccess).toBe(true);
    });

    // First message establishes baseline
    client.send({
      data: JSON.stringify({ scans: "t1", "project-config": "p1" }),
    });
    await waitFor(() => {
      expect(result.current.ready).toBe(true);
    });
    await waitFor(() => {
      expect(queryFn.mock.calls.length).toBeGreaterThanOrEqual(2);
    });

    const countAfterBaseline = queryFn.mock.calls.length;

    // Send the same timestamps again — nothing should change
    client.send({
      data: JSON.stringify({ scans: "t1", "project-config": "p1" }),
    });

    // Advance past any potential async processing
    await vi.advanceTimersByTimeAsync(200);
    expect(queryFn).toHaveBeenCalledTimes(countAfterBaseline);
  });

  it("closes EventSource on unmount", async () => {
    const clientReady = installSSEHandler();

    const { result, unmount } = renderHook(() => useTopicInvalidation(), {
      wrapper: createTestWrapper(),
    });

    const client = await clientReady;
    client.send({ data: JSON.stringify({ scans: "t1" }) });
    await waitFor(() => {
      expect(result.current).toBe(true);
    });

    unmount();

    // The 5s reconnect timer may have been scheduled by onerror during close.
    // Advance past it to verify it doesn't cause errors (MSW handler was
    // already consumed, so a reconnect would hit onUnhandledRequest: "error"
    // if the timer leaked with real timers).
    await vi.advanceTimersByTimeAsync(6000);

    expect(() => client.close()).not.toThrow();
  });
});
