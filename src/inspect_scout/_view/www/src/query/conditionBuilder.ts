import type {
  OperatorModel,
  LogicalOperatorModel,
  ConditionValue,
  Condition,
  SimpleCondition,
  CompoundCondition,
  ConditionBase,
  ConditionModel,
  ScalarValue,
} from "./types";
import { isScalarArray, isTuple } from "./types";

/**
 * Internal builder for creating Condition instances.
 *
 * Type assertions in this class are necessary because:
 * - Constructor accepts `compound: boolean` (TypeScript widens true|false to boolean)
 * - Discriminated union requires literal types (`compound: true` or `compound: false`)
 * - Factories guarantee correct literal values at runtime
 * - TypeScript can't statically prove constructor only receives literals
 *
 * This is acceptable because:
 * - Assertions are localized to this internal implementation
 * - Public API (serializers) has zero type assertions
 * - Standard pattern for builder + discriminated union
 */
export class ConditionBuilder implements ConditionBase {
  private constructor(
    public readonly left: string | Condition | null,
    public readonly operator: OperatorModel | LogicalOperatorModel,
    public readonly right: ConditionValue | null,
    public readonly compound: boolean
  ) {}

  // Factory for simple conditions
  static simple(
    field: string,
    operator: OperatorModel,
    value: ConditionValue
  ): SimpleCondition {
    const instance = new ConditionBuilder(field, operator, value, false);
    return instance as SimpleCondition;
  }

  // Factory for logical conditions
  static compound(
    operator: LogicalOperatorModel,
    left: Condition,
    right: Condition | null = null
  ): CompoundCondition {
    const instance = new ConditionBuilder(left, operator, right, true);
    return instance as CompoundCondition;
  }

  // Logical combinators (Python __and__, __or__, __invert__)
  and(other: Condition): Condition {
    // Safe cast: factories ensure compound is always a literal (true/false)
    return ConditionBuilder.compound("AND", this as Condition, other);
  }

  or(other: Condition): Condition {
    // Safe cast: factories ensure compound is always a literal (true/false)
    return ConditionBuilder.compound("OR", this as Condition, other);
  }

  not(): Condition {
    // Safe cast: factories ensure compound is always a literal (true/false)
    return ConditionBuilder.compound("NOT", this as Condition, null);
  }

  // Serialization for JSON.stringify()
  toJSON(): ConditionModel {
    if (this.compound) {
      // TypeScript needs help narrowing to CompoundCondition
      const self = this as CompoundCondition;
      return {
        is_compound: true,
        left: self.left.toJSON(),
        operator: self.operator,
        right: self.right ? self.right.toJSON() : null,
      };
    } else {
      // TypeScript needs help narrowing to SimpleCondition
      const self = this as SimpleCondition;
      return {
        is_compound: false,
        left: self.left,
        operator: self.operator,
        right: this.serializeValue(self.right),
      };
    }
  }

  private serializeValue(
    value: Exclude<ConditionValue, Condition> | null
  ): ConditionModel["right"] {
    if (value === null) return null;
    if (isScalarArray(value)) return value;
    if (isTuple(value)) return value;
    return value as ScalarValue;
  }
}
