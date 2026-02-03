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

import { ScanApi, TopicVersions } from "./api";
import {
  kMethodGetScan,
  kMethodGetScannerDataframe,
  kMethodGetScannerDataframeInput,
  kMethodGetScans,
  webViewJsonRpcClient,
} from "./jsonrpc";
import { createVSCodeStore } from "./vscode-storage";

export const apiVscodeV1 = (vscodeApi: VSCodeApi): ScanApi => {
  const rpcClient = webViewJsonRpcClient(vscodeApi);
  // Fetch scans data (used by both getScans and getScansDir)
  // Note: caching is handled by react-query at the hook level
  const fetchScansData = async (): Promise<{
    scans: Status[];
    results_dir: string;
  }> => {
    const response = (await rpcClient(kMethodGetScans, [])) as string;
    if (response) {
      return JSON5.parse<{ scans: Status[]; results_dir: string }>(response);
    }
    throw new Error("Invalid response for getScans");
  };

  return {
    capability: "scans",
    getConfig: async () => {
      const data = await fetchScansData();
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
    // eslint-disable-next-line @typescript-eslint/require-await
    hasTranscript: async (): Promise<never> => {
      throw new Error("Not Yet Implemented");
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
    getScan: async (_scansDir: string, scanPath: string): Promise<Status> => {
      const response = (await rpcClient(kMethodGetScan, [scanPath])) as string;

      if (response) {
        return JSON5.parse<Status>(response);
      } else {
        throw new Error(`Invalid response for getScan for scan: ${scanPath}`);
      }
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    getScans: async (_scansDir: string): Promise<ScansResponse> => {
      throw new Error("Not implemented in VSCode API v1");
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    getScansColumnValues: async (): Promise<never> => {
      throw new Error("Not implemented in VSCode API");
    },
    getScannerDataframe: async (
      _scansDir: string,
      scanPath: string,
      scanner: string
    ): Promise<Uint8Array> => {
      const response = await rpcClient(kMethodGetScannerDataframe, [
        scanPath,
        scanner,
      ]);
      if (response && response instanceof Uint8Array) {
        return response;
      } else {
        throw new Error(
          `Invalid response for getScannerDataframe for scan: ${scanPath}, scanner: ${scanner}`
        );
      }
    },
    getScannerDataframeInput: async (_scansDir, scanPath, scanner, uuid) => {
      const response = await rpcClient(kMethodGetScannerDataframeInput, [
        scanPath,
        scanner,
        uuid,
      ]);

      // Ensure we have the correct response
      if (!Array.isArray(response) || response.length !== 2) {
        throw new Error(
          `Invalid response for getScannerDataframeInput for scan: ${scanPath}, scanner: ${scanner}, uuid: ${uuid}`
        );
      }

      if (response) {
        const inputRaw = response[0];
        const inputTypeRaw = response[1];

        if (typeof inputRaw !== "string") {
          throw new Error(
            `Invalid input data for getScannerDataframeInput for scan: ${scanPath}, scanner: ${scanner}, uuid: ${uuid}`
          );
        }

        if (typeof inputTypeRaw !== "string") {
          throw new Error(
            `Invalid input type for getScannerDataframeInput for scan: ${scanPath}, scanner: ${scanner}, uuid: ${uuid}`
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
    // Noop for now since vs code
    connectTopicUpdates: (
      callback: (topVersions: TopicVersions) => void
    ): (() => void) => {
      callback({ "project-config": "yo" });
      return () => {};
    },
    // Validation API (not implemented for VSCode)
    // eslint-disable-next-line @typescript-eslint/require-await
    getValidationSets: async (): Promise<string[]> => {
      throw new Error("Not implemented in VSCode API");
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    getValidationCases: async (): Promise<never> => {
      throw new Error("Not implemented in VSCode API");
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    getValidationCase: async (): Promise<never> => {
      throw new Error("Not implemented in VSCode API");
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    createValidationSet: async (): Promise<never> => {
      throw new Error("Not implemented in VSCode API");
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    upsertValidationCase: async (): Promise<never> => {
      throw new Error("Not implemented in VSCode API");
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    deleteValidationCase: async (): Promise<never> => {
      throw new Error("Not implemented in VSCode API");
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    deleteValidationSet: async (): Promise<never> => {
      throw new Error("Not implemented in VSCode API");
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    renameValidationSet: async (): Promise<never> => {
      throw new Error("Not implemented in VSCode API");
    },
    storage: createVSCodeStore(vscodeApi),
  };
};
