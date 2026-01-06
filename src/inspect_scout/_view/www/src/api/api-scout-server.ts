import { ScanResultInputData, Input, InputType } from "../app/types";
import type { Condition, OrderByModel } from "../query";
import {
  AppConfig,
  Pagination,
  ScanJobsResponse,
  Status,
  Transcript,
  TranscriptsResponse,
} from "../types/api-types";
import { encodeBase64Url } from "../utils/base64url";
import { asyncJsonParse } from "../utils/json-worker";

import { NoPersistence, ScanApi } from "./api";
import { serverRequestApi } from "./request";

export type HeaderProvider = () => Promise<Record<string, string>>;

export const apiScoutServer = (
  options: {
    apiBaseUrl?: string;
    headerProvider?: HeaderProvider;
  } = {}
): ScanApi => {
  const { apiBaseUrl, headerProvider } = options;
  const requestApi = serverRequestApi(apiBaseUrl || "/api/v2", headerProvider);

  return {
    capability: "workbench",
    getConfig: async (): Promise<AppConfig> => {
      const result = await requestApi.fetchString("GET", `/config`);
      return asyncJsonParse<AppConfig>(result.raw);
    },
    getTranscripts: async (
      transcriptsDir: string,
      filter?: Condition,
      orderBy?: OrderByModel | OrderByModel[],
      pagination?: Pagination
    ): Promise<TranscriptsResponse> => {
      const result = await requestApi.fetchString(
        "POST",
        `/transcripts/${encodeBase64Url(transcriptsDir)}`,
        {},
        JSON.stringify({
          filter: filter ?? null,
          order_by: orderBy ?? null,
          pagination: pagination ?? null,
        })
      );

      const parsedResult = await asyncJsonParse<TranscriptsResponse>(
        result.raw
      );
      return parsedResult;
    },
    getTranscript: async (
      transcriptsDir: string,
      id: string
    ): Promise<Transcript> => {
      const result = await requestApi.fetchString(
        "GET",
        `/transcripts/${encodeBase64Url(transcriptsDir)}/${encodeURIComponent(id)}`
      );
      return asyncJsonParse<Transcript>(result.raw);
    },
    getScan: async (scanLocation: string): Promise<Status> => {
      const result = await requestApi.fetchString(
        "GET",
        `/scanjobs/${encodeBase64Url(scanLocation)}`
      );

      return asyncJsonParse<Status>(result.raw);
    },

    getScans: async (
      filter?: Condition,
      orderBy?: OrderByModel | OrderByModel[],
      pagination?: Pagination
    ): Promise<ScanJobsResponse> => {
      const result = await requestApi.fetchString(
        "POST",
        `/scanjobs`,
        {},
        JSON.stringify({
          filter: filter ?? null,
          order_by: orderBy ?? null,
          pagination: pagination ?? null,
        })
      );
      return asyncJsonParse<ScanJobsResponse>(result.raw);
    },
    getScannerDataframe: async (
      scanLocation: string,
      scanner: string
    ): Promise<ArrayBuffer> => {
      return await requestApi.fetchBytes(
        "GET",
        `/scanjobs/${encodeBase64Url(scanLocation)}/${encodeURIComponent(scanner)}`
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
        `/scanjobs/${encodeBase64Url(scanLocation)}/${encodeURIComponent(scanner)}/${encodeURIComponent(uuid)}/input`
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
