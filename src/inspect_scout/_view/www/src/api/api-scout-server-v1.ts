import { ScanResultInputData, Input, InputType } from "../app/types";
import {
  ActiveScansResponse,
  ProjectConfig,
  ProjectConfigInput,
  ScansResponse,
  Status,
  TranscriptsResponse,
} from "../types/api-types";
import { asyncJsonParse } from "../utils/json-worker";

import { NoPersistence, ScanApi } from "./api";
import { AsyncCache } from "./api-cache";
import { serverRequestApi } from "./request";

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
    getConfig: async () => {
      const data = await readScans();
      return {
        home_dir: "",
        project_dir: ".",
        scans_dir: data.results_dir,
        transcripts_dir: null,
      };
    },
    getProjectConfig(): Promise<{ config: ProjectConfig; etag: string }> {
      return null as any;
    },
    updateProjectConfig(
      _config: ProjectConfigInput,
      _etag: string
    ): Promise<{ config: ProjectConfig; etag: string }> {
      return null as any;
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
    getScan: async (scanLocation: string): Promise<Status> => {
      const result = await requestApi.fetchString(
        "GET",
        `/scan/${encodeURIComponent(scanLocation)}?status_only=true`
      );

      return asyncJsonParse<Status>(result.raw);
    },

    getScans: async (): Promise<ScansResponse> => {
      const result = await readScans();
      return {
        items: result.scans,
        total_count: result.scans.length,
        next_cursor: null,
      };
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
    // eslint-disable-next-line @typescript-eslint/require-await
    getActiveScans: async (): Promise<ActiveScansResponse> => {
      throw new Error("Not Yet Implemented");
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    postCode: async (): Promise<Record<string, string>> => {
      throw new Error("Not Yet Implemented");
    },
    storage: NoPersistence,
  };
};
