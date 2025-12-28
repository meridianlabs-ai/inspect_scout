import { ConditionBuilder } from "./conditionBuilder";
import type { Condition, OrderByModel, ScalarValue } from "./types";

export class Column {
  constructor(private readonly name: string) {}

  // Comparison operators (Python __eq__, __ne__, etc.)
  eq(value: ScalarValue): Condition {
    return value === null
      ? ConditionBuilder.simple(this.name, "IS NULL", null)
      : ConditionBuilder.simple(this.name, "=", value);
  }

  ne(value: ScalarValue): Condition {
    return value === null
      ? ConditionBuilder.simple(this.name, "IS NOT NULL", null)
      : ConditionBuilder.simple(this.name, "!=", value);
  }

  lt(value: ScalarValue): Condition {
    return ConditionBuilder.simple(this.name, "<", value);
  }

  lte(value: ScalarValue): Condition {
    return ConditionBuilder.simple(this.name, "<=", value);
  }

  gt(value: ScalarValue): Condition {
    return ConditionBuilder.simple(this.name, ">", value);
  }

  gte(value: ScalarValue): Condition {
    return ConditionBuilder.simple(this.name, ">=", value);
  }

  // List operators
  in(values: ScalarValue[]): Condition {
    return ConditionBuilder.simple(this.name, "IN", values);
  }

  notIn(values: ScalarValue[]): Condition {
    return ConditionBuilder.simple(this.name, "NOT IN", values);
  }

  // Pattern matching
  like(pattern: string): Condition {
    return ConditionBuilder.simple(this.name, "LIKE", pattern);
  }

  notLike(pattern: string): Condition {
    return ConditionBuilder.simple(this.name, "NOT LIKE", pattern);
  }

  ilike(pattern: string): Condition {
    return ConditionBuilder.simple(this.name, "ILIKE", pattern);
  }

  notIlike(pattern: string): Condition {
    return ConditionBuilder.simple(this.name, "NOT ILIKE", pattern);
  }

  // Null checks
  isNull(): Condition {
    return ConditionBuilder.simple(this.name, "IS NULL", null);
  }

  isNotNull(): Condition {
    return ConditionBuilder.simple(this.name, "IS NOT NULL", null);
  }

  // Range
  between(low: ScalarValue, high: ScalarValue): Condition {
    if (low === null || high === null) {
      throw new Error("BETWEEN requires non-null bounds");
    }
    return ConditionBuilder.simple(this.name, "BETWEEN", [low, high]);
  }

  notBetween(low: ScalarValue, high: ScalarValue): Condition {
    if (low === null || high === null) {
      throw new Error("NOT BETWEEN requires non-null bounds");
    }
    return ConditionBuilder.simple(this.name, "NOT BETWEEN", [low, high]);
  }

  // Sorting
  asc(): OrderByModel {
    return { column: this.name, direction: "ASC" };
  }

  desc(): OrderByModel {
    return { column: this.name, direction: "DESC" };
  }
}
