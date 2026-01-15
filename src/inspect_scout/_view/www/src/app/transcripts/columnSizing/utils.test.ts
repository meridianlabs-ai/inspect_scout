import { describe, expect, it } from "vitest";

import { TranscriptColumn } from "../columns";

import { clampSize, getColumnConstraints, getColumnId } from "./utils";

describe("clampSize", () => {
  const constraints = { size: 150, minSize: 50, maxSize: 200 };

  it("returns size unchanged when within constraints", () => {
    expect(clampSize(100, constraints)).toBe(100);
  });

  it("returns size at minSize boundary", () => {
    expect(clampSize(50, constraints)).toBe(50);
  });

  it("returns size at maxSize boundary", () => {
    expect(clampSize(200, constraints)).toBe(200);
  });

  it("clamps to minSize when below minimum", () => {
    expect(clampSize(30, constraints)).toBe(50);
  });

  it("clamps to maxSize when above maximum", () => {
    expect(clampSize(300, constraints)).toBe(200);
  });

  it("clamps negative values to minSize", () => {
    expect(clampSize(-10, constraints)).toBe(50);
  });
});

describe("getColumnConstraints", () => {
  it("extracts constraints from columns with all properties", () => {
    const columns: TranscriptColumn[] = [
      {
        accessorKey: "test",
        header: "Test",
        size: 100,
        minSize: 50,
        maxSize: 200,
      } as TranscriptColumn,
    ];

    const constraints = getColumnConstraints(columns);

    expect(constraints.get("test")).toEqual({
      size: 100,
      minSize: 50,
      maxSize: 200,
    });
  });

  it("uses default values when constraints not specified", () => {
    const columns: TranscriptColumn[] = [
      {
        accessorKey: "test",
        header: "Test",
      } as TranscriptColumn,
    ];

    const constraints = getColumnConstraints(columns);

    expect(constraints.get("test")).toEqual({
      size: 150, // DEFAULT_SIZE
      minSize: 40, // DEFAULT_MIN_SIZE
      maxSize: 600, // DEFAULT_MAX_SIZE
    });
  });

  it("uses column id when accessorKey not available", () => {
    const columns: TranscriptColumn[] = [
      {
        id: "custom-id",
        header: "Test",
        size: 120,
      } as TranscriptColumn,
    ];

    const constraints = getColumnConstraints(columns);

    expect(constraints.has("custom-id")).toBe(true);
    expect(constraints.get("custom-id")?.size).toBe(120);
  });

  it("handles multiple columns", () => {
    const columns: TranscriptColumn[] = [
      {
        accessorKey: "col1",
        header: "Column 1",
        size: 100,
        minSize: 60,
        maxSize: 200,
      } as TranscriptColumn,
      {
        accessorKey: "col2",
        header: "Column 2",
        size: 150,
        minSize: 80,
        maxSize: 300,
      } as TranscriptColumn,
    ];

    const constraints = getColumnConstraints(columns);

    expect(constraints.size).toBe(2);
    expect(constraints.get("col1")).toEqual({
      size: 100,
      minSize: 60,
      maxSize: 200,
    });
    expect(constraints.get("col2")).toEqual({
      size: 150,
      minSize: 80,
      maxSize: 300,
    });
  });

  it("returns empty map for empty columns array", () => {
    const constraints = getColumnConstraints([]);
    expect(constraints.size).toBe(0);
  });
});

describe("getColumnId", () => {
  it("returns accessorKey when available", () => {
    const column = {
      accessorKey: "test_key",
      header: "Test",
    } as TranscriptColumn;

    expect(getColumnId(column)).toBe("test_key");
  });

  it("returns id when accessorKey not available", () => {
    const column = {
      id: "custom_id",
      header: "Test",
    } as TranscriptColumn;

    expect(getColumnId(column)).toBe("custom_id");
  });

  it("prefers id over accessorKey when both present", () => {
    const column = {
      id: "custom_id",
      accessorKey: "accessor_key",
      header: "Test",
    } as TranscriptColumn;

    // id takes precedence since it's checked first
    expect(getColumnId(column)).toBe("custom_id");
  });

  it("returns empty string when neither id nor accessorKey present", () => {
    const column = {
      header: "Test",
    } as TranscriptColumn;

    expect(getColumnId(column)).toBe("");
  });
});
