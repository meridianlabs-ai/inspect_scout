/**
 * Branded types for nominal typing in TypeScript.
 *
 * Branded types create distinct types from the same base type,
 * preventing accidental misuse at compile time with zero runtime overhead.
 *
 * @example
 * ```ts
 * type UserId = Brand<number, "UserId">;
 * type PostId = Brand<number, "PostId">;
 *
 * const makeUserId = make<UserId>();
 * const makePostId = make<PostId>();
 *
 * const userId = makeUserId(42);
 * const postId = makePostId(42);
 * getUser(postId);  // ✗ compile error - PostId !== UserId
 * ```
 *
 * @module
 */

declare const __brand: unique symbol;

/**
 * Creates a branded type from a base type.
 *
 * The brand exists only at compile time—no runtime overhead.
 *
 * @typeParam Base - The underlying primitive or object type
 * @typeParam Branding - A unique type used to distinguish this brand (often the entity type itself)
 *
 * @example
 * ```ts
 * type UserId = Brand<number, User>;
 * type PostId = Brand<number, Post>;
 * // UserId and PostId are incompatible even though both are numbers
 * ```
 */
export type Brand<Base, Branding> = Base & { [__brand]: Branding };

/**
 * Extracts the base type from a branded type.
 *
 * @typeParam B - A branded type
 * @returns The underlying base type without the brand
 *
 * @example
 * ```ts
 * type UserId = Brand<number, User>;
 * type Base = BaseOf<UserId>;  // number
 * ```
 */
type BaseOf<B extends Brand<unknown, unknown>> = Omit<B, typeof __brand>;

/** A function that converts a base value into a branded value. */
type Brander<B extends Brand<unknown, unknown>> = (value: BaseOf<B>) => B;

/**
 * Creates a brander function for a given branded type.
 *
 * @typeParam B - The branded type to produce
 * @returns A function that casts base values to the branded type
 *
 * @example
 * ```ts
 * type UserId = Brand<number, "UserId">;
 * const makeUserId = make<UserId>();
 * const id = makeUserId(42);
 * ```
 */
export function make<B extends Brand<unknown, unknown>>(): Brander<B> {
  return (value: BaseOf<B>): B => value as B;
}
