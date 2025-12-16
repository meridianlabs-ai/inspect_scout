import { ScanResultInputData, Input, InputType } from "../app/types.ts";
import { Scans, Status } from "../types";
import { asyncJsonParse } from "../utils/json-worker.ts";

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
  const requestApi = serverRequestApi(apiBaseUrl || "/api/v2", headerProvider);
  return {
    getScan: async (scanLocation: string): Promise<Status> => {
      const result = await requestApi.fetchString(
        "GET",
        `/scan/${encodeURIComponent(scanLocation)}?status_only=true`
      );

      return asyncJsonParse<Status>(result.raw);
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
