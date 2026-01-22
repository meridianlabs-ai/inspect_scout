import { ScanResultInputData, Input, InputType } from "../app/types";
import {
  ActiveScansResponse,
  ProjectConfig,
  ProjectConfigInput,
  ScannersResponse,
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
    getConfigVersion: (): Promise<string> => {
      throw new Error("Not Yet Implemented");
    },
    getConfig: async () => {
      const data = await readScans();
      return {
        filter: [],
        home_dir: "",
        project_dir: ".",
        scans: { dir: data.results_dir, source: "project" },
        transcripts: null,
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
    // eslint-disable-next-line @typescript-eslint/require-await
    getTranscriptsColumnValues: async (): Promise<never> => {
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
    // eslint-disable-next-line @typescript-eslint/require-await
    startScan: async (): Promise<never> => {
      throw new Error("Not Yet Implemented");
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    getScanners: async (): Promise<ScannersResponse> => {
      throw new Error("Not Yet Implemented");
    },
    // Validation API (not implemented in v1)
    // eslint-disable-next-line @typescript-eslint/require-await
    getValidationSets: async (): Promise<string[]> => {
      throw new Error("Not implemented in API v1");
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    getValidationCases: async (): Promise<never> => {
      throw new Error("Not implemented in API v1");
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    createValidationSet: async (): Promise<never> => {
      throw new Error("Not implemented in API v1");
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    upsertValidationCase: async (): Promise<never> => {
      throw new Error("Not implemented in API v1");
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    deleteValidationCase: async (): Promise<never> => {
      throw new Error("Not implemented in API v1");
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    deleteValidationSet: async (): Promise<never> => {
      throw new Error("Not implemented in API v1");
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    renameValidationSet: async (): Promise<never> => {
      throw new Error("Not implemented in API v1");
    },
    storage: NoPersistence,
  };
};
