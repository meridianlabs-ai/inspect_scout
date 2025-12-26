// Re-export from generated types (they're in components.schemas)
import type { components } from "../types/generated";

/** SQL comparison operators. */
export type OperatorModel = components["schemas"]["Operator"];

/** Logical operators for combining conditions. */
export type LogicalOperatorModel = components["schemas"]["LogicalOperator"];

/** JSON representation of a Condition (matches Python Pydantic schema). */
export type ConditionModel =
  // FastAPI does this Input/Output thing for recursive types.
  | components["schemas"]["Condition-Input"]
  | components["schemas"]["Condition-Output"];

/** Scalar values that can be used in conditions (matching Python). */
export type ScalarValue = string | number | boolean | null;

/**
 * Base interface with shared methods for all conditions.
 */
export interface ConditionBase {
  /** Combine conditions with AND. */
  and(other: Condition): Condition;
  /** Combine conditions with OR. */
  or(other: Condition): Condition;
  /** Negate a condition with NOT. */
  not(): Condition;
  /** Serialize to JSON format (called automatically by JSON.stringify()). */
  toJSON(): ConditionModel;
}

/**
 * Simple condition: column comparison (e.g., model = "gpt-4").
 */
export interface SimpleCondition extends ConditionBase {
  /** Discriminant for simple conditions. */
  readonly compound: false;
  /** Column name. */
  readonly left: string;
  /** Comparison operator. */
  readonly operator: OperatorModel;
  /** Comparison value. */
  readonly right: Exclude<ConditionValue, Condition> | null;
}

/**
 * Compound condition: logical combination (e.g., AND, OR, NOT).
 */
export interface CompoundCondition extends ConditionBase {
  /** Discriminant for compound conditions. */
  readonly compound: true;
  /** Left operand. */
  readonly left: Condition;
  /** Logical operator. */
  readonly operator: LogicalOperatorModel;
  /** Right operand (null for NOT). */
  readonly right: Condition | null;
}

/**
 * WHERE clause condition that can be combined with others.
 *
 * Discriminated union enables TypeScript to automatically narrow types
 * based on the `compound` property without requiring type assertions.
 */
export type Condition = SimpleCondition | CompoundCondition;

// Internal builder types
export type ConditionValue =
  | ScalarValue
  | ScalarValue[]
  | [ScalarValue, ScalarValue] // BETWEEN tuple
  | Condition; // Nested condition

// Type guards for narrowing (optional with discriminated union, kept for semantic clarity)
export function isSimpleCondition(
  condition: Condition
): condition is SimpleCondition {
  return !condition.compound;
}

export function isCompoundCondition(
  condition: Condition
): condition is CompoundCondition {
  return condition.compound;
}

// Type guard utilities
export const isScalarArray = (val: unknown): val is ScalarValue[] =>
  Array.isArray(val) && !isTuple(val);

export const isTuple = (val: unknown): val is [ScalarValue, ScalarValue] =>
  Array.isArray(val) && val.length === 2;

/** Sort column specification for ORDER BY clauses (matches Python Pydantic schema). */
export type OrderByModel = components["schemas"]["OrderBy"];
