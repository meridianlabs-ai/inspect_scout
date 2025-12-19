import { useMemo } from "react";

import { AsyncData, loading } from "../utils/asyncData";

/**
 * The `useMapAsyncData` function is a custom React hook that transforms the data
 * in an `AsyncData` object or an array of `AsyncData` objects. It uses the `useMemo`
 * hook to avoid unnecessary recalculations.
 *
 * @template TBefore - The type of the data before the transformation
 * @template TAfter - The type of the data after the transformation
 * @param {AsyncData<TBefore> | AsyncData<TBefore>[]} input - The `AsyncData` object(s)
 * to transform
 * @param {(before: TBefore) => TAfter} transform - The function to transform the
 * data
 * @param {(err: Error) => Error} [errorTransform] - The function to transform any
 * errors (optional)
 * @returns {AsyncData<TAfter> | AsyncData<TAfter>[]} - The transformed `AsyncData`
 * object(s)
 *
 * @example
 * ```typescript
 * const asyncData = { loading: false, data: 5 };
 * const transform = (num: number) => num * 2;
 * const result = useMapAsyncData(asyncData, transform);
 * console.log(result); // { loading: false, data: 10 }
 * ```
 */
export function useMapAsyncData<TBefore, TAfter>(
  input: AsyncData<TBefore>,
  transform: (before: TBefore) => TAfter,
  errorTransform?: (err: Error) => Error
): AsyncData<TAfter>;
export function useMapAsyncData<TBefore, TAfter>(
  input: AsyncData<TBefore>[],
  transform: (before: TBefore) => TAfter,
  errorTransform?: (err: Error) => Error
): AsyncData<TAfter>[];
export function useMapAsyncData<TBefore, TAfter>(
  input: AsyncData<TBefore> | AsyncData<TBefore>[],
  transform: (before: TBefore) => TAfter,
  errorTransform?: (err: Error) => Error
): AsyncData<TAfter> | AsyncData<TAfter>[] {
  return useMemo(() => {
    const isArray = Array.isArray(input);
    const mapped = (isArray ? input : [input]).map<AsyncData<TAfter>>(
      (item) => {
        if (item.error) {
          const error = errorTransform
            ? errorTransform(item.error)
            : item.error;
          return { loading: false, error };
        }
        if (item.loading) return loading;

        try {
          return { loading: false, data: transform(item.data) };
        } catch (error: unknown) {
          if (!(error instanceof Error))
            throw Error(
              `useMapAsyncData only supports catching Error's: ${JSON.stringify(error)}`
            );
          return { loading: false, error };
        }
      }
    );
    if (!isArray) {
      const [onlyItem] = mapped;
      if (!onlyItem) throw Error("useMapAsyncData: Array must have one item.");
      return onlyItem;
    }
    return mapped;
  }, [input, transform, errorTransform]);
}
