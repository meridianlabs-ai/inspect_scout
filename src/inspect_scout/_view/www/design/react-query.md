# React Query Patterns

This document covers type-safe patterns for using TanStack Query (React Query) v5 in the frontend.

## Type-Safe Query Keys with `queryOptions`

### The Problem

React Query's `queryClient.setQueryData()` and `getQueryData()` don't inherently enforce type consistency. You can write data of one type and read it expecting another:

```typescript
// No compile-time error, but runtime disaster
queryClient.setQueryData(["scan", dir, path], scanRowData);  // ScanRow
const data = queryClient.getQueryData<Status>(["scan", dir, path]);  // Expects Status
```

### The Solution: DataTag

React Query v5 introduced `queryOptions()` which brands the query key with a `DataTag` containing type information:

```typescript
import { queryOptions } from "@tanstack/react-query";

export const scanDetailOptions = (api: ScanApi, scansDir: string, scanPath: string) =>
  queryOptions({
    queryKey: ["scan", scansDir, scanPath] as const,
    queryFn: (): Promise<Status> => api.getScan(scansDir, scanPath),
    staleTime: 10000,
  });
```

The returned `queryKey` is typed as `DataTag<["scan", string, string], Status, Error>`.

### Type-Safe Cache Operations

When you use the tagged key, TypeScript enforces type consistency:

```typescript
const options = scanDetailOptions(api, scansDir, scanPath);

// TypeScript infers the correct type
const data = queryClient.getQueryData(options.queryKey);
//    ^? Status | undefined

// Compile error: ScanRow is not assignable to Status
queryClient.setQueryData(options.queryKey, scanRowData);
```

## Query Options Factory Pattern

Define query options in a centralized file for reuse:

```typescript
// src/app/server/scanQueries.ts
import { queryOptions } from "@tanstack/react-query";

export const scansListOptions = (api: ScanApi, scansDir: string) =>
  queryOptions({
    queryKey: ["scans", scansDir] as const,
    queryFn: async (): Promise<ScanRow[]> => {
      const response = await api.getScans(scansDir);
      return response.items;
    },
    staleTime: 5000,
    refetchInterval: 5000,
  });
```

Then use in hooks:

```typescript
export const useScans = (scansDir: string): AsyncData<ScanRow[]> => {
  const api = useApi();
  return useAsyncDataFromQuery(scansListOptions(api, scansDir));
};
```

## Conditional Queries with `skipToken`

`skipToken` is used to disable a query until required parameters are available. This is common for dependent queries where you need to wait for user selection or parent data before fetching.

### Example: Fetching a Selected Scan

```typescript
import { skipToken } from "@tanstack/react-query";

type ScanParams = { scansDir: string; scanPath: string };

// The hook accepts either valid params or skipToken
export const useScan = (
  params: ScanParams | typeof skipToken
): AsyncData<Status> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey:
      params === skipToken
        ? [skipToken]  // All disabled queries share this key
        : ["scan", params.scansDir, params.scanPath],
    queryFn:
      params === skipToken
        ? skipToken  // Query won't execute
        : () => api.getScan(params.scansDir, params.scanPath),
    staleTime: 10000,
  });
};

// Usage: query is disabled until scanPath is available
const { data } = useScan(
  scanPath ? { scansDir, scanPath } : skipToken
);
```

## References

- [The Query Options API - TkDodo](https://tkdodo.eu/blog/the-query-options-api)
- [Type-safe React Query - TkDodo](https://tkdodo.eu/blog/type-safe-react-query)
