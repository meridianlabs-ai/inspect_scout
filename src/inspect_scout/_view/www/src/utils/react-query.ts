import { ApiError } from "../api/request";

declare global {
  // Set by e2e tests to skip retry delays

  var __TEST_DISABLE_RETRY: boolean | undefined;
}

export const defaultRetry = (failureCount: number, error: Error): boolean =>
  !globalThis.__TEST_DISABLE_RETRY &&
  failureCount < 3 &&
  !(error instanceof ApiError && !isRetryableHttpStatus(error.status));

// see https://cloud.google.com/storage/docs/retry-strategy
const isRetryableHttpStatus = (status: number): boolean =>
  status === 408 || status === 429 || (status >= 500 && status < 600);
