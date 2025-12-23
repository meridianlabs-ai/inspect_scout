import { ScanResultInputData, Input, InputType } from "../app/types.ts";
import {
  Status,
  ScanResultInputData as GeneratedInputResponse,
} from "../types";
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
    getScansDir: async (): Promise<string> => {
      return (await requestApi.fetchString("GET", `/scans-dir`)).raw;
    },
    getScan: async (scanLocation: string): Promise<Status> => {
      const result = await requestApi.fetchString(
        "GET",
        `/scans/${base64url(scanLocation)}`
      );

      return asyncJsonParse<Status>(result.raw);
    },

    getScans: async (scansDir?: string): Promise<Status[]> => {
      const dir = scansDir ?? resultsDir;
      const query = dir
        ? `/scans?results_dir=${encodeURIComponent(dir)}`
        : "/scans";
      return (
        await requestApi.fetchType<Status[]>("GET", query, {
          enableBrowserCache: true,
        })
      ).parsed;
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
      // Fetch the data as JSON
      const response = await requestApi.fetchType<GeneratedInputResponse>(
        "GET",
        `/scans/${base64url(scanLocation)}/${encodeURIComponent(scanner)}/${encodeURIComponent(uuid)}/input`
      );
      const data = response.parsed;

      if (data.input_type === "event") {
        const foo = data.input;
      } else if (data.input_type === "message") {
        const foo = data.input;
      }

      // Map snake_case → camelCase for frontend convention
      return {
        input: data.input as Input,
        inputType: data.input_type as InputType,
      };
    },
    storage: NoPersistence,
  };
};

/**
 * Encodes a string as base64url (URL-safe base64 without padding).
 */
const base64url = (s: string) =>
  btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
