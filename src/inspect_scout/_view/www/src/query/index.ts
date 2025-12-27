/**
 * Query builder for constructing complex filter conditions.
 *
 * Provides a fluent API for building conditions that serialize automatically with JSON.stringify().
 *
 * @example Basic usage
 * ```typescript
 * import { transcriptColumns } from "@/query";
 *
 * // Simple condition
 * const filter = transcriptColumns.model.eq("gpt-4");
 *
 * // Serialize to JSON (automatically via .toJSON())
 * const json = filter.toJSON();
 * // { is_compound: false, left: "model", operator: "=", right: "gpt-4" }
 * ```
 *
 * @example Combining conditions
 * ```typescript
 * // AND operator
 * const andFilter = transcriptColumns.model.eq("gpt-4")
 *   .and(transcriptColumns.score.gt(0.8));
 *
 * // OR operator
 * const orFilter = transcriptColumns.model.eq("gpt-4")
 *   .or(transcriptColumns.error.isNull());
 *
 * // Complex nested expression
 * const complex = transcriptColumns.task_set.eq("math")
 *   .and(transcriptColumns.score.between(0.7, 1.0))
 *   .or(transcriptColumns.error.isNull());
 * ```
 *
 * @example All operators
 * ```typescript
 * // Comparison
 * transcriptColumns.score.eq(0.8)
 * transcriptColumns.score.ne(0)
 * transcriptColumns.score.lt(0.5)
 * transcriptColumns.score.lte(0.5)
 * transcriptColumns.score.gt(0.8)
 * transcriptColumns.score.gte(0.8)
 *
 * // Lists
 * transcriptColumns.model.in(["gpt-4", "claude-3"])
 * transcriptColumns.model.notIn(["error"])
 *
 * // Pattern matching
 * transcriptColumns.error.like("%timeout%")
 * transcriptColumns.error.notLike("%success%")
 * transcriptColumns.error.ilike("%error%")      // case-insensitive
 * transcriptColumns.error.notIlike("%ok%")
 *
 * // Range
 * transcriptColumns.score.between(0.7, 1.0)
 * transcriptColumns.score.notBetween(0, 0.3)
 *
 * // Null checks
 * transcriptColumns.error.isNull()
 * transcriptColumns.error.isNotNull()
 *
 * // NOT operator
 * transcriptColumns.success.eq(true).not()
 * ```
 *
 * @example Dynamic field access
 * ```typescript
 * // Predefined fields
 * transcriptColumns.model
 * transcriptColumns.score
 * transcriptColumns.transcript_id
 *
 * // Dynamic fields via Proxy
 * transcriptColumns.custom_field.eq("value")
 *
 * // JSON paths
 * transcriptColumns.field("metadata.task.id").eq(123)
 * ```
 *
 * @example Using with fetch
 * ```typescript
 * // POST with JSON body - JSON.stringify() automatically calls .toJSON()
 * const filter = transcriptColumns.model.eq("gpt-4").and(transcriptColumns.score.gt(0.8));
 * fetch("/api/transcripts", {
 *   method: "POST",
 *   body: JSON.stringify({ filter })
 * });
 * ```
 *
 * @module query
 */

// Core classes
export { Column } from "./column";
export { ConditionBuilder } from "./conditionBuilder";
export { TranscriptColumns, transcriptColumns } from "./transcriptColumns";

// Types
export type {
  OperatorModel,
  LogicalOperatorModel,
  ConditionModel,
  OrderByModel,
  ScalarValue,
  ConditionValue,
  Condition,
} from "./types";

// Type guards
export { isScalarArray, isTuple } from "./types";
