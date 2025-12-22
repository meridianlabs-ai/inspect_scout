import { QueryKey, useQuery, UseQueryOptions } from "@tanstack/react-query";
import { useMemo } from "react";

import { AsyncData, loading } from "./asyncData";

/**
 * Custom hook that retrieves data using `useQuery` from the `@tanstack/react-query`
 * library. It wraps the `QueryResult` from the hook in a simpler `AsyncData`.
 *
 * @param options - An object of type `UseQueryOptions`.
 * @returns An object of type `AsyncData`. If the query is pending, it returns a
 * loading state. If there's an error, it returns an object with the error and loading
 * state as false. If the query is successful, it returns the data and loading state
 * as false.
 */
export function useAsyncDataFromQuery<
  TQueryFnData = unknown,
  TData = TQueryFnData,
  TQueryKey extends QueryKey = QueryKey,
>(
  options: UseQueryOptions<TQueryFnData, Error, TData, TQueryKey>
): AsyncData<TData> {
  const { isPending, isError, error, data } = useQuery(options);
  return useMemo(() => {
    if (isPending) return loading;
    if (isError) return { error, loading: false };

    return { data, loading: false };
  }, [isPending, isError, error, data]);
}
