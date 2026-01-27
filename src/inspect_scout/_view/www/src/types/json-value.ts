/**
 * JSON value type - any valid JSON value.
 *
 * Uses interfaces for array/object to avoid TS2589 "excessively deep"
 * errors with immer's type inference on recursive type aliases.
 */
export type JsonValue =
  | null
  | boolean
  | number
  | string
  | JsonArray
  | JsonObject;

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export interface JsonArray extends Array<JsonValue> {}
export interface JsonObject {
  [key: string]: JsonValue;
}
