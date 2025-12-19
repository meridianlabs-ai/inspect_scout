/**
 * AsyncData represents the possible states of some asynchronous operation like
 * a network request to an API. When the request is first made, it's `loading`,
 * but once we get a response, it will either represent the requested `data` or
 * maybe the operation failed due to an `error`.
 *
 * @typeParam T - the data that will be returned
 */
export type AsyncData<T> = AsyncDataLoading | AsyncDataNotLoading<T>;

export type AsyncDataLoading = {
  data?: undefined;
  loading: true;
  error?: undefined;
};

/**
 * The different states the async data can be in when loading is finished.
 *
 * @typeParam T - the data type that can be returned when error is undefined
 */
export type AsyncDataNotLoading<T> =
  | {
      data: T;
      loading: false;
      error?: undefined;
    }
  | {
      data?: undefined;
      loading: false;
      error: Error;
    };

type AsyncDataMap<Mapping> = { [K in keyof Mapping]: AsyncData<Mapping[K]> };
/**
 * The `compose` function allows a set of `AsyncData` values to be combined into a single
 * `AsyncData`. The complex type of the function represents a transformation
 * from an argument like this...
 *
 *   {
 *     a: AsyncData<A>,
 *     b: AsyncData<B>,
 *     c: AsyncData<C>
 *   }
 *
 * ...to a return value like this...
 *
 *   AsyncData<{
 *     a: A,
 *     b: B,
 *     c: C
 *   }>
 *
 * In practice, this can be used to create hooks that depend on multiple API
 * calls.
 *
 */
export function compose<Mapping>(
  hooks: AsyncDataMap<Mapping>
): AsyncData<Mapping> {
  const result = {} as Mapping;
  const errors: Error[] = [];
  let loadingResult = false;

  for (const key in hooks) {
    const { loading, error, data } = hooks[key];

    if (error) {
      errors.push(error);
    } else if (loading) {
      loadingResult = true;
    } else {
      result[key] = data;
    }
  }

  // If any `AsyncData` has an error, we know the entire set of operations will
  // not succeed. Right now we return the first error, but the keys of JS
  // objects don't have a defined order. Potentially in the future, we'll want
  // to represent the entire set of errors somehow, allowing the caller to
  // prioritize the errors as they'd like.
  if (errors[0]) {
    return { loading: false, error: errors[0] };
  }

  if (loadingResult) {
    return loading;
  }

  return { loading: false, data: result };
}

/**
 * The `data` function wraps the provided data in an `AsyncData` object, indicating that the data is not loading and there is no error.
 *
 * @template T - The type of the data
 * @param {T} data - The data to wrap
 * @returns {AsyncData<T>} - An `AsyncData` object with `loading` set to `false` and `data` set to the provided data
 */
export function data<T>(data: T): AsyncData<T> {
  return { loading: false, data };
}

/**
 * The `loading` constant is an instance of `AsyncDataLoading` that can be shared to provide identity stability. It represents the state when the data is loading.
 */
export const loading: AsyncDataLoading = { loading: true };
