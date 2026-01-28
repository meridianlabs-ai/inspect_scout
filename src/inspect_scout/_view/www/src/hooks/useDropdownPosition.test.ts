// @vitest-environment jsdom
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useDropdownPosition } from "./useDropdownPosition";

describe("useDropdownPosition", () => {
  const originalInnerHeight = window.innerHeight;

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    Object.defineProperty(window, "innerHeight", {
      value: originalInnerHeight,
      writable: true,
    });
  });

  it("returns 'below' when there is plenty of space below the element", () => {
    Object.defineProperty(window, "innerHeight", {
      value: 1000,
      writable: true,
    });

    const { result } = renderHook(() =>
      useDropdownPosition({ optionCount: 5 })
    );

    // Create a mock element positioned near the top
    const mockElement = document.createElement("div");
    vi.spyOn(mockElement, "getBoundingClientRect").mockReturnValue({
      bottom: 100,
      top: 80,
      left: 0,
      right: 100,
      width: 100,
      height: 20,
      x: 0,
      y: 80,
      toJSON: () => ({}),
    });

    // Attach the ref
    act(() => {
      result.current.ref(mockElement);
    });

    expect(result.current.position).toBe("below");
  });

  it("returns 'above' when there is insufficient space below the element", () => {
    Object.defineProperty(window, "innerHeight", {
      value: 500,
      writable: true,
    });

    const { result } = renderHook(() =>
      useDropdownPosition({ optionCount: 10 })
    );

    // Create a mock element positioned near the bottom
    const mockElement = document.createElement("div");
    vi.spyOn(mockElement, "getBoundingClientRect").mockReturnValue({
      bottom: 450,
      top: 430,
      left: 0,
      right: 100,
      width: 100,
      height: 20,
      x: 0,
      y: 430,
      toJSON: () => ({}),
    });

    act(() => {
      result.current.ref(mockElement);
    });

    // Space below = 500 - 450 = 50px
    // Dropdown height = 10 * 22 + 8 = 228px
    // 50 < 228, so should be 'above'
    expect(result.current.position).toBe("above");
  });

  it("updates position on window resize", () => {
    Object.defineProperty(window, "innerHeight", {
      value: 1000,
      writable: true,
    });

    const { result } = renderHook(() =>
      useDropdownPosition({ optionCount: 10 })
    );

    const mockElement = document.createElement("div");
    vi.spyOn(mockElement, "getBoundingClientRect").mockReturnValue({
      bottom: 800,
      top: 780,
      left: 0,
      right: 100,
      width: 100,
      height: 20,
      x: 0,
      y: 780,
      toJSON: () => ({}),
    });

    act(() => {
      result.current.ref(mockElement);
    });

    // Initial: space below = 1000 - 800 = 200px, dropdown = 228px -> 'above'
    expect(result.current.position).toBe("above");

    // Simulate window resize to larger height
    Object.defineProperty(window, "innerHeight", {
      value: 1200,
      writable: true,
    });

    act(() => {
      window.dispatchEvent(new Event("resize"));
      vi.advanceTimersByTime(100);
    });

    // After resize: space below = 1200 - 800 = 400px, dropdown = 228px -> 'below'
    expect(result.current.position).toBe("below");
  });

  it("handles null element gracefully", () => {
    const { result } = renderHook(() =>
      useDropdownPosition({ optionCount: 5 })
    );

    // Default position should be 'below' when no element is attached
    expect(result.current.position).toBe("below");

    // Attaching and detaching null should not throw
    act(() => {
      result.current.ref(null);
    });

    expect(result.current.position).toBe("below");
  });

  it("respects custom optionHeight and maxVisibleOptions", () => {
    Object.defineProperty(window, "innerHeight", {
      value: 500,
      writable: true,
    });

    const { result } = renderHook(() =>
      useDropdownPosition({
        optionCount: 20,
        optionHeight: 30,
        maxVisibleOptions: 5,
        padding: 10,
      })
    );

    const mockElement = document.createElement("div");
    vi.spyOn(mockElement, "getBoundingClientRect").mockReturnValue({
      bottom: 340,
      top: 320,
      left: 0,
      right: 100,
      width: 100,
      height: 20,
      x: 0,
      y: 320,
      toJSON: () => ({}),
    });

    act(() => {
      result.current.ref(mockElement);
    });

    // Space below = 500 - 340 = 160px
    // Dropdown height = min(20, 5) * 30 + 10 = 5 * 30 + 10 = 160px
    // 160 >= 160, so should be 'below'
    expect(result.current.position).toBe("below");
  });

  it("updates position on scroll events", () => {
    Object.defineProperty(window, "innerHeight", {
      value: 600,
      writable: true,
    });

    const { result } = renderHook(() =>
      useDropdownPosition({ optionCount: 10 })
    );

    let bottomValue = 300;
    const mockElement = document.createElement("div");
    vi.spyOn(mockElement, "getBoundingClientRect").mockImplementation(() => ({
      bottom: bottomValue,
      top: bottomValue - 20,
      left: 0,
      right: 100,
      width: 100,
      height: 20,
      x: 0,
      y: bottomValue - 20,
      toJSON: () => ({}),
    }));

    act(() => {
      result.current.ref(mockElement);
    });

    // Initial: space below = 600 - 300 = 300px, dropdown = 228px -> 'below'
    expect(result.current.position).toBe("below");

    // Simulate scroll that moves element closer to bottom
    bottomValue = 550;

    act(() => {
      window.dispatchEvent(new Event("scroll"));
      vi.advanceTimersByTime(100);
    });

    // After scroll: space below = 600 - 550 = 50px, dropdown = 228px -> 'above'
    expect(result.current.position).toBe("above");
  });
});
