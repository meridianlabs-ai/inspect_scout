/**
 * Minimal async cache with promise deduplication and TTL-based expiration.
 * Prevents concurrent duplicate requests by caching in-flight promises.
 */

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

export class AsyncCache<T> {
  private cache = new Map<string, CacheEntry<T>>();
  private inflightRequests = new Map<string, Promise<T>>();

  constructor(private defaultTtlMs: number = 10000) {}

  /**
   * Gets data from cache or fetches it using the provided fetcher function.
   * Concurrent requests for the same key will return the same promise.
   *
   * @param key - Cache key
   * @param fetcher - Async function to fetch data if not cached
   * @param ttlMs - Time-to-live in milliseconds (optional, uses default if not provided)
   * @returns Promise resolving to cached or freshly fetched data
   */
  async get(
    key: string,
    fetcher: () => Promise<T>,
    ttlMs?: number
  ): Promise<T> {
    const ttl = ttlMs ?? this.defaultTtlMs;

    // Check if we have a valid cached entry
    const cached = this.cache.get(key);
    if (cached && Date.now() - cached.timestamp < ttl) {
      return cached.data;
    }

    // Check if there's already an in-flight request for this key
    const inflight = this.inflightRequests.get(key);
    if (inflight) {
      return inflight;
    }

    // Create new request
    const request = fetcher()
      .then((data) => {
        // Cache the result
        this.cache.set(key, { data, timestamp: Date.now() });
        return data;
      })
      .finally(() => {
        // Remove from in-flight requests
        this.inflightRequests.delete(key);
      });

    // Store in-flight request
    this.inflightRequests.set(key, request);

    return request;
  }

  /**
   * Invalidates cache entries. If key is provided, only that entry is removed.
   * Otherwise, all entries are cleared.
   *
   * @param key - Optional cache key to invalidate
   */
  invalidate(key?: string): void {
    if (key) {
      this.cache.delete(key);
    } else {
      this.cache.clear();
    }
  }

  /**
   * Clears all cached data and in-flight requests.
   */
  clear(): void {
    this.cache.clear();
    this.inflightRequests.clear();
  }
}
