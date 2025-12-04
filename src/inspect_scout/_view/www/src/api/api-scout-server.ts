import { Scans, Status } from "../types";

import { NoPersistence, ScanApi } from "./api";
import { serverRequestApi } from "./request.ts";

export type HeaderProvider = () => Promise<Record<string, string>>;

export const apiScoutServer = (
  options: {
    apiBaseUrl?: string;
    headerProvider?: HeaderProvider;
    resultsDir?: string;
  } = {}
): ScanApi => {
  const { apiBaseUrl, headerProvider, resultsDir } = options;
  const requestApi = serverRequestApi(apiBaseUrl || "/api", headerProvider);
  return {
    getScan: async (scanLocation: string): Promise<Status> => {
      const result = await requestApi.fetchType<Status>(
        "GET",
        `/scan/${encodeURIComponent(scanLocation)}?status_only=true`,
      );
      return result.parsed;
    },

    getScans: async (): Promise<Scans> => {
      let query = "/scans?status_only=true";
      if (resultsDir) {
        query += `&results_dir=${encodeURIComponent(resultsDir)}`;
      }
      return (await requestApi.fetchType<Scans>("GET", query)).parsed;
    },
    getScannerDataframe: async (
      scanLocation: string,
      scanner: string
    ): Promise<ArrayBuffer> => {
      return await requestApi.fetchBytes(
        "GET",
        `/scanner_df/${encodeURIComponent(
          scanLocation
        )}?scanner=${encodeURIComponent(scanner)}&exclude_columns=input`
      );
    },
    getScannerField: async (
      scanLocation: string,
      scanner: string,
      row: string,
      column: string,
    ): Promise<any> => {
      return (await requestApi.fetchType<any>(
        "GET",
        `/scanner/${encodeURIComponent(scanLocation)}/${encodeURIComponent(scanner)}/${encodeURIComponent(row)}/${encodeURIComponent(column)}`
      )).parsed;
    },
    storage: NoPersistence,
  };
};
