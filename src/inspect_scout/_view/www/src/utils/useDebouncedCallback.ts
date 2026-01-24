import { debounce, DebouncedFunc } from "lodash-es";
import { useEffect, useLayoutEffect, useMemo, useRef } from "react";

/**
 * Creates a debounced version of a callback that always calls the latest version.
 *
 * Unlike `useMemo(() => debounce(fn), [])`, this hook ensures the debounced function
 * always invokes the most recent callback, eliminating the need for refs to access
 * current state values.
 *
 * @param callback - The function to debounce. Can close over current state/props.
 * @param delay - Debounce delay in milliseconds
 * @returns A stable debounced function that calls the latest callback
 *
 * @example
 * const debouncedSave = useDebouncedCallback(() => {
 *   // Access current state directly - no refs needed
 *   if (!workingCase) return;
 *   mutation.mutate({ data: workingCase });
 * }, 600);
 */
export function useDebouncedCallback<T extends (...args: unknown[]) => unknown>(
  callback: T,
  delay: number
): DebouncedFunc<(...args: Parameters<T>) => void> {
  const callbackRef = useRef(callback);

  // Keep ref pointing to latest callback (useLayoutEffect for synchronous update)
  useLayoutEffect(() => {
    callbackRef.current = callback;
  });

  // Create stable debounced function once
  const debouncedFn = useMemo(
    () =>
      debounce((...args: Parameters<T>) => {
        callbackRef.current(...args);
      }, delay),
    [delay]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      debouncedFn.cancel();
    };
  }, [debouncedFn]);

  return debouncedFn;
}
