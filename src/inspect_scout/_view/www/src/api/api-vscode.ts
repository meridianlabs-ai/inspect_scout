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
    getItem: (_key: string): string | null => {
      const state = api.getState();
      if (typeof state === "string") {
        return state;
      }
      return null;
    },
    setItem: (_key: string, value: string): void => {
      api.setState(value);
    },
    removeItem: (_key: string): void => {
      api.setState(null);
    },
  };
};
