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
    getTranscriptsDir: async (): Promise<string> => {
      return (await requestApi.fetchString("GET", `/transcripts-dir`)).raw;
    },
    getTranscripts: async (transcriptsDir?: string): Promise<unknown[]> => {
      const result = await requestApi.fetchString(
        "GET",
        transcriptsDir
          ? `/transcripts?dir=${encodeURIComponent(transcriptsDir)}`
          : `/transcripts`
      );

      const parsedResult = await asyncJsonParse<unknown[]>(result.raw);
      if (!Array.isArray(parsedResult)) {
        throw new Error("Expected array from /transcripts endpoint");
      }
      return parsedResult;
    },
    getScan: async (scanLocation: string): Promise<Status> => {
      const result = await requestApi.fetchString(
        "GET",
        `/scans/${base64url(scanLocation)}`
      );

      return asyncJsonParse<Status>(result.raw);
    },

    getScans: async (): Promise<Scans> => {
      let query = "/scans";
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
        `/scans/${base64url(scanLocation)}/${encodeURIComponent(scanner)}`
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
        `/scans/${base64url(scanLocation)}/${encodeURIComponent(scanner)}/${encodeURIComponent(uuid)}/input`
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

/**
 * Encodes a string as base64url (URL-safe base64 without padding).
 */
const base64url = (s: string) =>
  btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
