import JSON5 from "json5";

import { Input, InputType } from "../app/types";
import { Condition } from "../query/types";
import {
  ActiveScansResponse,
  ProjectConfig,
  ProjectConfigInput,
  ScannersResponse,
  ScansResponse,
  Status,
  TranscriptsResponse,
} from "../types/api-types";
import { VSCodeApi } from "../utils/vscode";

import { ClientStorage, ScanApi } from "./api";
import { AsyncCache } from "./api-cache";
import {
  kMethodGetScan,
  kMethodGetScannerDataframe,
  kMethodGetScannerDataframeInput,
  kMethodGetScans,
} from "./jsonrpc";

export const apiVscode = (
  vscodeApi: VSCodeApi,
  rpcClient: (method: string, params?: unknown) => Promise<unknown>,
  cacheTtlMs: number = 10000
): ScanApi => {
  // Cache for scans data with promise deduplication and TTL-based expiration
  // VSCode API uses a single cache key since the scan list is tied to the extension instance
  const scansCache = new AsyncCache<{ scans: Status[]; results_dir: string }>(
    cacheTtlMs
  );

  // Shared method to fetch scans data (used by both getScans and getScansDir)
  const fetchScansData = async (): Promise<{
    scans: Status[];
    results_dir: string;
  }> => {
    return scansCache.get("vscode-scans", async () => {
      const response = (await rpcClient(kMethodGetScans, [])) as string;
      if (response) {
        const result = JSON5.parse<{ scans: Status[]; results_dir: string }>(
          response
        );
        // For VSCode, we don't have a separate scansDir, so we use empty string
        return { scans: result.scans, results_dir: result.results_dir };
      } else {
        throw new Error("Invalid response for getScans");
      }
    });
  };

  return {
    capability: "scans",
    // eslint-disable-next-line @typescript-eslint/require-await
    getConfigVersion: async (): Promise<string> => {
      throw new Error("Not Yet Implemented");
    },
    getConfig: async () => {
      const data = await fetchScansData();
      return {
        home_dir: "",
        project_dir: ".",
        scans_dir: { dir: data.results_dir, source: "project" },
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
    // eslint-disable-next-line @typescript-eslint/require-await
    getTranscripts: async (
      _transcriptsDir?: string,
      _filter?: Condition
    ): Promise<TranscriptsResponse> => {
      throw new Error("Not Yet Implemented");
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    getTranscript: async (): Promise<never> => {
      throw new Error("Not Yet Implemented");
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    getTranscriptsColumnValues: async (): Promise<never> => {
      throw new Error("Not Yet Implemented");
    },
    getScan: async (scanLocation: string): Promise<Status> => {
      const response = (await rpcClient(kMethodGetScan, [
        scanLocation,
      ])) as string;

      if (response) {
        return JSON5.parse<Status>(response);
      } else {
        throw new Error(
          `Invalid response for getScan for scan: ${scanLocation}`
        );
      }
    },
    getScans: async (): Promise<ScansResponse> => {
      const data = await fetchScansData();
      return {
        items: data.scans,
        total_count: data.scans.length,
        next_cursor: null,
      };
    },
    getScannerDataframe: async (
      scanLocation: string,
      scanner: string
    ): Promise<Uint8Array> => {
      const response = await rpcClient(kMethodGetScannerDataframe, [
        scanLocation,
        scanner,
      ]);
      if (response && response instanceof Uint8Array) {
        return response;
      } else {
        throw new Error(
          `Invalid response for getScannerDataframe for scan: ${scanLocation}, scanner: ${scanner}`
        );
      }
    },
    getScannerDataframeInput: async (scanLocation, scanner, uuid) => {
      const response = await rpcClient(kMethodGetScannerDataframeInput, [
        scanLocation,
        scanner,
        uuid,
      ]);

      // Ensure we have the correct response
      if (!Array.isArray(response) || response.length !== 2) {
        throw new Error(
          `Invalid response for getScannerDataframeInput for scan: ${scanLocation}, scanner: ${scanner}, uuid: ${uuid}`
        );
      }

      if (response) {
        const inputRaw = response[0];
        const inputTypeRaw = response[1];

        if (typeof inputRaw !== "string") {
          throw new Error(
            `Invalid input data for getScannerDataframeInput for scan: ${scanLocation}, scanner: ${scanner}, uuid: ${uuid}`
          );
        }

        if (typeof inputTypeRaw !== "string") {
          throw new Error(
            `Invalid input type for getScannerDataframeInput for scan: ${scanLocation}, scanner: ${scanner}, uuid: ${uuid}`
          );
        }

        const input = JSON5.parse<Input>(inputRaw);
        const inputType = inputTypeRaw as InputType;
        return { input, inputType };
      } else {
        throw new Error("Invalid response for getScans");
      }
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
    storage: createVSCodeStore(vscodeApi),
  };
};

const createVSCodeStore = (api: VSCodeApi): ClientStorage => {
  return {
    getItem: (key: string): string | null => {
      const state = api.getState();

      // VSCode stores a single state object, so we need to parse it and extract by key
      if (state && typeof state === "object") {
        const stateObj = state as Record<string, string>;
        const value = stateObj[key];
        return value || null;
      }

      return null;
    },
    setItem: (key: string, value: string): void => {
      // Get existing state object or create new one
      const existingState = api.getState() || {};
      const stateObj = (
        typeof existingState === "object" ? existingState : {}
      ) as Record<string, string>;

      // Update the specific key
      stateObj[key] = value;

      // Save the entire state object back
      api.setState(stateObj);
    },
    removeItem: (key: string): void => {
      const existingState = api.getState();
      if (existingState && typeof existingState === "object") {
        const stateObj = existingState as Record<string, string>;
        delete stateObj[key];
        api.setState(stateObj);
      }
    },
  };
};
