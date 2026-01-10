import { ApiError } from "../api/request";

export const defaultRetry = (failureCount: number, error: Error): boolean =>
  failureCount < 3 &&
  !(error instanceof ApiError && !isRetryableHttpStatus(error.status));

// see https://cloud.google.com/storage/docs/retry-strategy
const isRetryableHttpStatus = (status: number): boolean =>
  status === 408 || status === 429 || (status >= 500 && status < 600);
