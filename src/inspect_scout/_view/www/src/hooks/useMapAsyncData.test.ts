// @vitest-environment jsdom
import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { data, loading } from "../utils/asyncData";

import { useMapAsyncData } from "./useMapAsyncData";

describe("useMapAsyncData", () => {
  it("transforms the data in an AsyncData object", () => {
    const { result } = renderHook(() =>
      useMapAsyncData(data(5), (num: number) => num * 2)
    );
    expect(result.current).toEqual(data(10));
  });

  it("transforms the data in an array of AsyncData objects", () => {
    const { result } = renderHook(() =>
      useMapAsyncData([data(5), data(10)], (num: number) => num * 2)
    );
    expect(result.current).toEqual([data(10), data(20)]);
  });

  it("returns the input as is if it is in a loading state", () => {
    const { result } = renderHook(() =>
      useMapAsyncData(loading, (num: number) => num * 2)
    );
    expect(result.current).toEqual(loading);
  });

  it("transforms any errors in the AsyncData object", () => {
    const { result } = renderHook(() =>
      useMapAsyncData(
        { loading: false, error: new Error("test error") },
        (x) => x,
        (err: Error) => new Error(err.message.toUpperCase())
      )
    );
    expect(result.current.error).toEqual(new Error("TEST ERROR"));
  });
});
