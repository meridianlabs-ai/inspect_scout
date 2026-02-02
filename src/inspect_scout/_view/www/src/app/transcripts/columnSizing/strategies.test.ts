import { describe, expect, it } from "vitest";

import { TranscriptInfo } from "../../../types/api-types";
import {
  getSizingStrategy,
  sizingStrategies,
  SizingStrategy,
} from "../../components/columnSizing";
import { TranscriptColumn } from "../columns";

describe("sizingStrategies", () => {
  describe("default strategy", () => {
    const strategy = sizingStrategies.default as SizingStrategy<TranscriptInfo>;

    it("extracts sizes from columns", () => {
      const columns: TranscriptColumn[] = [
        {
          accessorKey: "col1",
          header: "Column 1",
          size: 100,
        } as TranscriptColumn,
        {
          accessorKey: "col2",
          header: "Column 2",
          size: 200,
        } as TranscriptColumn,
      ];

      const sizes = strategy.computeSizes({
        tableElement: null,
        columns,
        data: [],
        constraints: new Map(),
      });

      expect(sizes).toEqual({
        col1: 100,
        col2: 200,
      });
    });

    it("skips columns without size", () => {
      const columns: TranscriptColumn[] = [
        {
          accessorKey: "col1",
          header: "Column 1",
          size: 100,
        } as TranscriptColumn,
        {
          accessorKey: "col2",
          header: "Column 2",
        } as TranscriptColumn,
      ];

      const sizes = strategy.computeSizes({
        tableElement: null,
        columns,
        data: [],
        constraints: new Map(),
      });

      expect(sizes).toEqual({
        col1: 100,
      });
      expect(sizes.col2).toBeUndefined();
    });

    it("returns empty object for empty columns", () => {
      const sizes = strategy.computeSizes({
        tableElement: null,
        columns: [],
        data: [],
        constraints: new Map(),
      });
      expect(sizes).toEqual({});
    });
  });

  describe("fit-content strategy", () => {
    const strategy = sizingStrategies[
      "fit-content"
    ] as SizingStrategy<TranscriptInfo>;

    it("falls back to default sizes when no table element", () => {
      const columns: TranscriptColumn[] = [
        {
          accessorKey: "col1",
          header: "Column 1",
          size: 100,
        } as TranscriptColumn,
      ];

      const sizes = strategy.computeSizes({
        tableElement: null,
        columns,
        data: [],
        constraints: new Map(),
      });

      expect(sizes).toEqual({
        col1: 100,
      });
    });

    it("falls back to DEFAULT_SIZE when column has no size", () => {
      const columns: TranscriptColumn[] = [
        {
          accessorKey: "col1",
          header: "Column 1",
        } as TranscriptColumn,
      ];

      const sizes = strategy.computeSizes({
        tableElement: null,
        columns,
        data: [],
        constraints: new Map(),
      });

      expect(sizes).toEqual({
        col1: 150, // DEFAULT_SIZE
      });
    });
  });
});

describe("getSizingStrategy", () => {
  it("returns default strategy for 'default' key", () => {
    const strategy = getSizingStrategy("default");
    expect(strategy).toBe(sizingStrategies.default);
  });

  it("returns fit-content strategy for 'fit-content' key", () => {
    const strategy = getSizingStrategy("fit-content");
    expect(strategy).toBe(sizingStrategies["fit-content"]);
  });
});
