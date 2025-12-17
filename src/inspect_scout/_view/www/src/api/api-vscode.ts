import JSON5 from "json5";

import { Input, InputType } from "../app/types";
import { Scans, Status } from "../types";
import { VSCodeApi } from "../utils/vscode";

import { ClientStorage, ScanApi } from "./api";
import {
  kMethodGetScan,
  kMethodGetScannerDataframe,
  kMethodGetScannerDataframeInput,
  kMethodGetScans,
} from "./jsonrpc";

export const apiVscode = (
  vscodeApi: VSCodeApi,
  rpcClient: (method: string, params?: unknown) => Promise<unknown>
): ScanApi => {
  return {
    // eslint-disable-next-line @typescript-eslint/require-await
    getTranscriptsDir: async (): Promise<string> => {
      throw new Error("Not Yet Implemented");
    },
    // eslint-disable-next-line @typescript-eslint/require-await
    getTranscripts: async (_transcriptsDir?: string): Promise<unknown[]> => {
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
    getScans: async (): Promise<Scans> => {
      const response = (await rpcClient(kMethodGetScans, [])) as string;
      if (response) {
        return JSON5.parse<Scans>(response);
      } else {
        throw new Error("Invalid response for getScans");
      }
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
