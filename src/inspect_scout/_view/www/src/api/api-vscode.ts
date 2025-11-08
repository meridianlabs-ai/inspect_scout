import JSON5 from "json5";

import { Results, Scans } from "../types";
import { VSCodeApi } from "../utils/vscode";

import { ClientStorage, ScanApi } from "./api";
import { kMethodGetScan, kMethodGetScans } from "./jsonrpc";

export const apiVscode = (
  vscodeApi: VSCodeApi,
  rpcClient: (method: string, params?: unknown) => Promise<unknown>
): ScanApi => {
  return {
    getScan: async (scanLocation: string): Promise<Results> => {
      const response = (await rpcClient(kMethodGetScan, [
        scanLocation,
      ])) as string;
      if (response) {
        return JSON5.parse<Results>(response);
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
