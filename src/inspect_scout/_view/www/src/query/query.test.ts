import { describe, expect, it } from "vitest";

import type { ConditionModel } from "./types";

import { transcriptColumns } from "./index";

describe("Column comparisons", () => {
  it("eq with scalar", () => {
    const condition = transcriptColumns.model.eq("gpt-4");
    expect(condition.toJSON()).toEqual({
      is_compound: false,
      left: "model",
      operator: "=",
      right: "gpt-4",
    });
  });

  it("eq with null converts to IS NULL", () => {
    const condition = transcriptColumns.error.eq(null);
    expect(condition.toJSON()).toEqual({
      is_compound: false,
      left: "error",
      operator: "IS NULL",
      right: null,
    });
  });

  it.each([
    ["ne", "!=", 100],
    ["lt", "<", 50],
    ["lte", "<=", 50],
    ["gt", ">", 75],
    ["gte", ">=", 75],
  ] as const)("%s operator", (method, operator, value) => {
    const condition = transcriptColumns.score[method](value);
    expect(condition.toJSON()).toMatchObject({
      operator,
      right: value,
    });
  });

  it("ne with null converts to IS NOT NULL", () => {
    const condition = transcriptColumns.error.ne(null);
    expect(condition.toJSON().operator).toBe("IS NOT NULL");
  });
});

describe("Column list operators", () => {
  it("in with multiple values", () => {
    const condition = transcriptColumns.model.in(["gpt-4", "claude-3"]);
    expect(condition.toJSON()).toEqual({
      is_compound: false,
      left: "model",
      operator: "IN",
      right: ["gpt-4", "claude-3"],
    });
  });

  it("notIn with values", () => {
    const condition = transcriptColumns.model.notIn(["error", "pending"]);
    expect(condition.toJSON().operator).toBe("NOT IN");
  });
});

describe("Column pattern matching", () => {
  it.each([
    ["like", "LIKE", "%error%"],
    ["notLike", "NOT LIKE", "%success%"],
    ["ilike", "ILIKE", "%Error%"],
    ["notIlike", "NOT ILIKE", "%Success%"],
  ] as const)("%s operator", (method, operator, pattern) => {
    const condition = transcriptColumns.error[method](pattern);
    expect(condition.toJSON()).toMatchObject({
      operator,
      right: pattern,
    });
  });
});

describe("Column null checks", () => {
  it("isNull", () => {
    const condition = transcriptColumns.error.isNull();
    expect(condition.toJSON()).toEqual({
      is_compound: false,
      left: "error",
      operator: "IS NULL",
      right: null,
    });
  });

  it("isNotNull", () => {
    const condition = transcriptColumns.limit.isNotNull();
    expect(condition.toJSON().operator).toBe("IS NOT NULL");
  });
});

describe("Column range operators", () => {
  it("between with valid bounds", () => {
    const condition = transcriptColumns.score.between(0.5, 0.9);
    expect(condition.toJSON()).toEqual({
      is_compound: false,
      left: "score",
      operator: "BETWEEN",
      right: [0.5, 0.9],
    });
  });

  it("between with null throws", () => {
    expect(() => transcriptColumns.score.between(null, 1)).toThrow(
      "BETWEEN requires non-null bounds"
    );
  });

  it("notBetween", () => {
    const condition = transcriptColumns.total_time.notBetween(0, 100);
    expect(condition.toJSON().operator).toBe("NOT BETWEEN");
  });
});

describe("Logical combinators", () => {
  it("and combines conditions", () => {
    const c1 = transcriptColumns.model.eq("gpt-4");
    const c2 = transcriptColumns.score.gt(0.8);
    const combined = c1.and(c2);

    const json = combined.toJSON();
    expect(json.is_compound).toBe(true);
    expect(json.operator).toBe("AND");
    expect(json.left).toEqual(c1.toJSON());
    expect(json.right).toEqual(c2.toJSON());
  });

  it("or combines conditions", () => {
    const combined = transcriptColumns.model
      .eq("error")
      .or(transcriptColumns.score.gt(3));
    expect(combined.toJSON().operator).toBe("OR");
  });

  it("not negates condition", () => {
    const condition = transcriptColumns.success.eq(true).not();
    const json = condition.toJSON();

    expect(json.is_compound).toBe(true);
    expect(json.operator).toBe("NOT");
    expect(json.right).toBeNull();
  });

  it("complex expression", () => {
    // (model = "gpt-4" AND score > 0.8) OR (status = "error")
    const filter = transcriptColumns.model
      .eq("gpt-4")
      .and(transcriptColumns.score.gt(0.8))
      .or(transcriptColumns.model.eq("error"));

    const json = filter.toJSON();
    expect(json.operator).toBe("OR");
    if (json.is_compound && json.left && typeof json.left !== "string") {
      expect(json.left.operator).toBe("AND");
    }
  });
});

describe("Dynamic field access", () => {
  it("predefined fields", () => {
    expect(transcriptColumns.model).toBeDefined();
    expect(transcriptColumns.score).toBeDefined();
  });

  it("dynamic fields via proxy", () => {
    const condition = transcriptColumns.field("custom_field").eq("value");
    expect(condition.toJSON().left).toBe("custom_field");
  });

  it("JSON path via field()", () => {
    const condition = transcriptColumns.field("metadata.task.id").eq(123);
    expect(condition.toJSON().left).toBe("metadata.task.id");
  });
});

describe("JSON serialization", () => {
  it("roundtrip serialization", () => {
    const original = transcriptColumns.model
      .eq("gpt-4")
      .and(transcriptColumns.score.between(0.7, 1.0));

    const json = original.toJSON();
    const serialized = JSON.stringify(json);
    const deserialized = JSON.parse(serialized) as ConditionModel;

    expect(deserialized).toEqual(json);
  });

  it("nested conditions serialize correctly", () => {
    const nested = transcriptColumns.model
      .eq("a")
      .and(transcriptColumns.score.eq(2).or(transcriptColumns.limit.eq(3)));

    const json = nested.toJSON();
    expect(json.operator).toBe("AND");
    if (
      json.is_compound &&
      json.right &&
      typeof json.right === "object" &&
      !Array.isArray(json.right) &&
      "operator" in json.right
    ) {
      expect(json.right.operator).toBe("OR");
    }
  });

  it("toJSON() method works with JSON.stringify()", () => {
    const filter = transcriptColumns.model
      .eq("gpt-4")
      .and(transcriptColumns.score.gt(0.8));

    // JSON.stringify() should automatically call .toJSON()
    const serialized = JSON.stringify({ filter });
    const parsed = JSON.parse(serialized);

    expect(parsed.filter).toEqual({
      is_compound: true,
      operator: "AND",
      left: {
        is_compound: false,
        left: "model",
        operator: "=",
        right: "gpt-4",
      },
      right: {
        is_compound: false,
        left: "score",
        operator: ">",
        right: 0.8,
      },
    });
  });

  it("JSON.stringify() works directly on condition", () => {
    const filter = transcriptColumns.model.eq("gpt-4");

    // JSON.stringify() should work directly on the condition
    const serialized = JSON.stringify(filter);
    const parsed = JSON.parse(serialized) as ConditionModel;

    expect(parsed).toEqual({
      is_compound: false,
      left: "model",
      operator: "=",
      right: "gpt-4",
    });
  });

  it("JSON.stringify() works on complex nested conditions", () => {
    const filter = transcriptColumns.model
      .eq("gpt-4")
      .and(transcriptColumns.score.between(0.7, 1.0))
      .or(transcriptColumns.error.isNull());

    const serialized = JSON.stringify(filter);
    const parsed = JSON.parse(serialized) as ConditionModel;

    // Verify the top-level OR
    expect(parsed.is_compound).toBe(true);
    expect(parsed.operator).toBe("OR");

    // Verify the nested AND on the left side
    if (parsed.is_compound && parsed.left && typeof parsed.left !== "string") {
      expect(parsed.left.operator).toBe("AND");
    }

    // Verify the IS NULL on the right side
    if (
      parsed.is_compound &&
      parsed.right &&
      typeof parsed.right === "object" &&
      !Array.isArray(parsed.right) &&
      "operator" in parsed.right
    ) {
      expect(parsed.right.operator).toBe("IS NULL");
    }
  });
});
