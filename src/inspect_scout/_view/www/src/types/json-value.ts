/**
 * JSON value type.
 *
 * openapi-typescript cannot generate this correctly because it inlines
 * recursive $refs, causing TS2502 circular reference errors. A truly
 * recursive type causes TS2589 with immer's deep type inference.
 *
 * Uses unknown for nested values as a pragmatic tradeoff.
 */
export type JsonValue =
  | null
  | boolean
  | number
  | string
  | unknown[]
  | { [key: string]: unknown };
