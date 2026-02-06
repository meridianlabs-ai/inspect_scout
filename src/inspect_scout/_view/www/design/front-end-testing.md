# Frontend Testing

## Prefer Integration Tests

<!-- cSpell:ignore Dodds -->
["Write tests, not too many, mostly integration."](https://kentcdodds.com/blog/write-tests) — Kent C. Dodds

Integration tests exercise multiple units together and minimize mocking. This gives higher confidence per test — a single test that runs through the hook, React Query, and the API layer catches wiring bugs that isolated unit tests miss. Mocking internal modules (e.g., `vi.mock()`) couples tests to implementation details.

## MSW (Mock Service Worker)

Network-level mocking for API hook tests ([Stop mocking fetch](https://kentcdodds.com/blog/stop-mocking-fetch)). MSW intercepts `fetch` so the real API layer runs end-to-end. Request/response assertions verify what actually goes over the wire, and handlers are portable across test frameworks.

For example, the `PUT` to `/project/config` requires an `If-Match` header for optimistic concurrency. A `vi.mock()` test that stubs `api.updateProjectConfig()` would pass even if the API layer forgot the header — the real `fetch` never fires. An MSW test catches this because it inspects the actual request:

```typescript
http.put("/api/v2/project/config", async ({ request }) => {
  capturedHeaders = new Headers(request.headers);
  return HttpResponse.json(updatedConfig);
});

// Fails if the API layer drops the header
expect(capturedHeaders?.get("If-Match")).toBe('"v1"');
```

| File | Purpose |
|------|---------|
| `src/test/setup-msw.ts` | Server lifecycle — `beforeAll`/`afterEach`/`afterAll` |
| `src/test/test-utils.tsx` | `createTestWrapper()` — provides QueryClient + ApiProvider |

**Setup**: MSW runs automatically via `vitest.config.ts` `setupFiles`. No per-test setup needed.

**Config**: `onUnhandledRequest: "error"` — any fetch not handled by a test handler fails the test. QueryClient uses `retry: false`, `gcTime: 0` for deterministic behavior.

**Collapsed group suppression**: Node has no concept of `console.groupCollapsed` — it prints everything. `setup-msw.ts` replicates browser behavior by suppressing `console.log` calls inside collapsed groups. This quiets MSW's SSE handler (which wraps all logging in `groupCollapsed`), but applies to any code using collapsed groups. Top-level `console.log` is unaffected.


### Type-check mock response data

Always pass the response type to `HttpResponse.json<T>()`. Without it, mock data silently drifts from the real API schema — missing fields, wrong types, stale shapes after a backend change — and tests pass against payloads the server would never return.

```typescript
http.get("/api/v2/scans/active", () =>
  HttpResponse.json<ActiveScansResponse>({
    items: { "scan-123": scanInfo },
  }),
);
```

## Patterns

### Hooks

**Shared QueryClient across hooks**: Pass the same `wrapper` to multiple `renderHook` calls.
```typescript
const wrapper = createTestWrapper();
const { result: queryResult } = renderHook(() => useQuery(...), { wrapper });
const { result: mutationResult } = renderHook(() => useMutation(...), { wrapper });
```

**skipToken**: Verify the query stays in loading state and no request is made.
```typescript
server.use(http.get("/api/v2/endpoint", () => { requestMade = true; ... }));
renderHook(() => useHook(skipToken), { wrapper: createTestWrapper() });
expect(result.current.loading).toBe(true);
await new Promise((r) => setTimeout(r, 50));
expect(requestMade).toBe(false);
```