import { ColumnTable } from "arquero";

import { Results } from "../types";

// Externalize the storage of a large results object
// when it exceeds this amount (to avoid perf issues)
const kExternalizeThresholdMB = 10;

interface ResultsCache {
  results?: Results;
  decodedScanners: Map<string, ColumnTable>;
}

// Module-level ref to store large results objects outside of Zustand
// This prevents Immer from creating expensive proxies for large data
let resultsCache: ResultsCache = {
  results: undefined,
  decodedScanners: new Map(),
};

export const resultsRef = {
  getResults: (): Results | undefined => {
    return resultsCache.results;
  },

  setResults: (results: Results): void => {
    // Clear caches when new results loaded
    resultsCache = {
      results,
      decodedScanners: new Map(),
    };
  },

  clearResults: (): void => {
    resultsCache = {
      results: undefined,
      decodedScanners: new Map(),
    };
  },

  getDecodedScanner: (scannerName: string): ColumnTable | undefined => {
    return resultsCache.decodedScanners.get(scannerName);
  },

  setDecodedScanner: (scannerName: string, table: ColumnTable): void => {
    resultsCache.decodedScanners.set(scannerName, table);
  },

  // Get a lightweight identifier for triggering renders
  getResultsIdentifier: ():
    | { location: string; complete: boolean }
    | undefined => {
    return resultsCache.results
      ? {
          location: resultsCache.results.location,
          complete: resultsCache.results.complete,
        }
      : undefined;
  },
};

// Determine whether the results are considered large
export const isLargeResults = (results: Results): boolean => {
  const totalSize = Object.values(results.scanners).reduce(
    (sum, scanner) => sum + (scanner.data?.length || 0),
    0
  );

  // Consider large if > NMB of data
  const isLarge = totalSize > kExternalizeThresholdMB * 1024 * 1024;
  return isLarge;
};
