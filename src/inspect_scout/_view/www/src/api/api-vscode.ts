import JSON5 from "json5";

import { Results, Scans } from "../types";
import { VSCodeApi } from "../utils/vscode";

import { NoPersistence, ScanApi } from "./api";
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
    storage: NoPersistence,
  };
};
