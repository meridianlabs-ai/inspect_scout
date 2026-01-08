// @vitest-environment jsdom
import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { usePreviousValue } from "./usePreviousValue";

describe("usePreviousValue", () => {
  it("returns undefined on the first render", () => {
    const { result } = renderHook(() => usePreviousValue(10));
    expect(result.current).toBeUndefined();
  });

  it("returns the previous value after a re-render with a new value", () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePreviousValue(value),
      {
        initialProps: { value: 10 },
      }
    );

    // First render: should return undefined
    expect(result.current).toBeUndefined();

    // Re-render with new value
    rerender({ value: 20 });
    expect(result.current).toBe(10);
  });

  it("tracks multiple value changes correctly", () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePreviousValue(value),
      {
        initialProps: { value: "first" },
      }
    );

    expect(result.current).toBeUndefined();

    rerender({ value: "second" });
    expect(result.current).toBe("first");

    rerender({ value: "third" });
    expect(result.current).toBe("second");

    rerender({ value: "fourth" });
    expect(result.current).toBe("third");
  });

  it("returns the same previous value when the current value does not change", () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePreviousValue(value),
      {
        initialProps: { value: 42 },
      }
    );

    expect(result.current).toBeUndefined();

    rerender({ value: 100 });
    expect(result.current).toBe(42);

    // Re-render with the same value
    rerender({ value: 100 });
    expect(result.current).toBe(42);

    // Re-render again with the same value
    rerender({ value: 100 });
    expect(result.current).toBe(42);
  });

  it("works with complex object types", () => {
    type User = { id: number; name: string };

    const user1: User = { id: 1, name: "Alice" };
    const user2: User = { id: 2, name: "Bob" };

    const { result, rerender } = renderHook(
      ({ value }) => usePreviousValue(value),
      {
        initialProps: { value: user1 },
      }
    );

    expect(result.current).toBeUndefined();

    rerender({ value: user2 });
    expect(result.current).toEqual(user1);
  });

  it("works with null values", () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePreviousValue(value),
      {
        initialProps: { value: null as string | null },
      }
    );

    expect(result.current).toBeUndefined();

    rerender({ value: "not null" });
    expect(result.current).toBeNull();

    rerender({ value: null });
    expect(result.current).toBe("not null");
  });

  it("works with boolean values", () => {
    const { result, rerender } = renderHook(
      ({ value }) => usePreviousValue(value),
      {
        initialProps: { value: true },
      }
    );

    expect(result.current).toBeUndefined();

    rerender({ value: false });
    expect(result.current).toBe(true);

    rerender({ value: true });
    expect(result.current).toBe(false);
  });

  it("works with array values", () => {
    const arr1 = [1, 2, 3];
    const arr2 = [4, 5, 6];

    const { result, rerender } = renderHook(
      ({ value }) => usePreviousValue(value),
      {
        initialProps: { value: arr1 },
      }
    );

    expect(result.current).toBeUndefined();

    rerender({ value: arr2 });
    expect(result.current).toEqual(arr1);
  });
});
