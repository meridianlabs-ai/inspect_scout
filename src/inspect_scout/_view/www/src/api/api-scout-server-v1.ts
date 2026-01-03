import { ScanResultInputData, Input, InputType } from "../app/types.ts";
import { Status } from "../types";
import { ScanJobsResponse, TranscriptsResponse } from "../types/api-types.ts";
import { asyncJsonParse } from "../utils/json-worker.ts";

import { NoPersistence, ScanApi } from "./api";
import { AsyncCache } from "./api-cache.ts";
import { serverRequestApi } from "./request.ts";

export type HeaderProvider = () => Promise<Record<string, string>>;

export const apiScoutServerV1 = (
  options: {
    apiBaseUrl?: string;
    headerProvider?: HeaderProvider;
    resultsDir?: string;
  } = {}
): ScanApi => {
  const { apiBaseUrl, headerProvider, resultsDir } = options;
  const requestApi = serverRequestApi(apiBaseUrl || "/api", headerProvider);

  // Cache for scans data with promise deduplication and TTL-based expiration
  const scansCache = new AsyncCache<{ scans: Status[]; results_dir: string }>(
    10000
  );

  const readScans = async () => {
    // Use resultsDir as cache key (or "default" if not specified)
    const cacheKey = resultsDir || "default";

    return scansCache.get(cacheKey, async () => {
      let query = "/scans?status_only=true";
      if (resultsDir) {
        query += `&results_dir=${encodeURIComponent(resultsDir)}`;
      }
      const response = (
        await requestApi.fetchType<{ scans: Status[]; results_dir: string }>(
          "GET",
          query
        )
      ).parsed;

      return response;
    });
  };

  return {
    capability: "scans",
    getTranscriptsDir: (): Promise<string> => {
      throw new Error("Not implemented in API v1");
    },
    getTranscripts: (
      _transcriptsDir?: string,
      _filter?: unknown
    ): Promise<TranscriptsResponse> => {
      throw new Error("Not implemented in API v1");
    },
    getTranscript: (): Promise<never> => {
      throw new Error("Not implemented in API v1");
    },
    getScansDir: async (): Promise<string> => {
      const result = await readScans();
      return result.results_dir;
    },
    getScan: async (scanLocation: string): Promise<Status> => {
      const result = await requestApi.fetchString(
        "GET",
        `/scan/${encodeURIComponent(scanLocation)}?status_only=true`
      );

      return asyncJsonParse<Status>(result.raw);
    },

    getScans: async (): Promise<ScanJobsResponse> => {
      const result = await readScans();
      return { items: result.scans, total_count: result.scans.length, next_cursor: null };
    },
    getScannerDataframe: async (
      scanLocation: string,
      scanner: string
    ): Promise<ArrayBuffer> => {
      return await requestApi.fetchBytes(
        "GET",
        `/scanner_df/${encodeURIComponent(
          scanLocation
        )}?scanner=${encodeURIComponent(scanner)}`
      );
    },
    getScannerDataframeInput: async (
      scanLocation: string,
      scanner: string,
      uuid: string
    ): Promise<ScanResultInputData> => {
      // Fetch the data
      const response = await requestApi.fetchType<Input>(
        "GET",
        `/scanner_df_input/${encodeURIComponent(
          scanLocation
        )}?scanner=${encodeURIComponent(scanner)}&uuid=${encodeURIComponent(uuid)}`
      );
      const input = response.parsed;

      // Read header to determine the input type
      const inputType = response.headers.get("X-Input-Type");
      if (!inputType) {
        throw new Error("Missing input type from server");
      }
      if (
        !["transcript", "message", "messages", "event", "events"].includes(
          inputType
        )
      ) {
        throw new Error(`Unknown input type from server: ${inputType}`);
      }

      // Return the DataFrameInput
      return { input, inputType: inputType as InputType };
    },
    storage: NoPersistence,
  };
};
