import { ScanResultInputData, Input, InputType } from "../app/types";
import type { Condition, OrderByModel } from "../query";
import {
  ActiveScansResponse,
  AppConfig,
  Pagination,
  ProjectConfig,
  ProjectConfigInput,
  ScanJobConfig,
  ScannersResponse,
  ScansResponse,
  Status,
  Transcript,
  TranscriptsResponse,
} from "../types/api-types";
import { encodeBase64Url } from "../utils/base64url";
import { asyncJsonParse } from "../utils/json-worker";

import { NoPersistence, ScanApi, ScalarValue, TopicVersions } from "./api";
import { serverRequestApi } from "./request";

export type HeaderProvider = () => Promise<Record<string, string>>;

export const apiScoutServer = (
  options: {
    apiBaseUrl?: string;
    headerProvider?: HeaderProvider;
  } = {}
): ScanApi => {
  const { apiBaseUrl = "/api/v2", headerProvider } = options;
  const requestApi = serverRequestApi(apiBaseUrl, headerProvider);

  return {
    capability: "workbench",
    getConfig: async (): Promise<AppConfig> => {
      const result = await requestApi.fetchString("GET", `/app-config`);
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
    getTranscriptsColumnValues: async (
      transcriptsDir: string,
      column: string,
      filter: Condition
    ): Promise<ScalarValue[]> => {
      const result = await requestApi.fetchString(
        "POST",
        `/transcripts/${encodeBase64Url(transcriptsDir)}/distinct`,
        {},
        JSON.stringify({ column, filter: filter ?? null })
      );
      return asyncJsonParse<ScalarValue[]>(result.raw);
    },
    getScan: async (scansDir: string, scanPath: string): Promise<Status> => {
      const result = await requestApi.fetchString(
        "GET",
        `/scans/${encodeBase64Url(scansDir)}/${encodeBase64Url(scanPath)}`
      );

      return asyncJsonParse<Status>(result.raw);
    },

    getScans: async (
      scansDir: string,
      filter?: Condition,
      orderBy?: OrderByModel | OrderByModel[],
      pagination?: Pagination
    ): Promise<ScansResponse> => {
      const result = await requestApi.fetchString(
        "POST",
        `/scans/${encodeBase64Url(scansDir)}`,
        {},
        JSON.stringify({
          filter: filter ?? null,
          order_by: orderBy ?? null,
          pagination: pagination ?? null,
        })
      );
      return asyncJsonParse<ScansResponse>(result.raw);
    },
    getScannerDataframe: async (
      scansDir: string,
      scanPath: string,
      scanner: string
    ): Promise<ArrayBuffer> => {
      return await requestApi.fetchBytes(
        "GET",
        `/scans/${encodeBase64Url(scansDir)}/${encodeBase64Url(scanPath)}/${encodeURIComponent(scanner)}`
      );
    },
    getScannerDataframeInput: async (
      scansDir: string,
      scanPath: string,
      scanner: string,
      uuid: string
    ): Promise<ScanResultInputData> => {
      // Fetch the data
      const response = await requestApi.fetchType<Input>(
        "GET",
        `/scans/${encodeBase64Url(scansDir)}/${encodeBase64Url(scanPath)}/${encodeURIComponent(scanner)}/${encodeURIComponent(uuid)}/input`
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
    getActiveScans: async (): Promise<ActiveScansResponse> =>
      asyncJsonParse<ActiveScansResponse>(
        (await requestApi.fetchString("GET", `/scans/active`)).raw
      ),
    postCode: async (condition: Condition): Promise<Record<string, string>> =>
      asyncJsonParse<Record<string, string>>(
        (
          await requestApi.fetchString(
            "POST",
            `/code`,
            {},
            JSON.stringify(condition)
          )
        ).raw
      ),
    getProjectConfig: async (): Promise<{
      config: ProjectConfig;
      etag: string;
    }> => {
      const response = await requestApi.fetchType<ProjectConfig>(
        "GET",
        `/project/config`
      );
      const etag = response.headers.get("ETag")?.replace(/"/g, "") ?? "";
      return { config: response.parsed, etag };
    },
    updateProjectConfig: async (
      config: ProjectConfigInput,
      etag: string | null
    ): Promise<{ config: ProjectConfig; etag: string }> => {
      const headers: Record<string, string> = {};
      if (etag) {
        headers["If-Match"] = `"${etag}"`;
      }
      const response = await requestApi.fetchType<ProjectConfig>(
        "PUT",
        `/project/config`,
        {
          headers,
          body: JSON.stringify(config),
        }
      );
      const newEtag = response.headers.get("ETag")?.replace(/"/g, "") ?? "";
      return { config: response.parsed, etag: newEtag };
    },
    startScan: async (config: ScanJobConfig): Promise<Status> =>
      asyncJsonParse<Status>(
        (
          await requestApi.fetchString(
            "POST",
            `/startscan`,
            {},
            JSON.stringify(config)
          )
        ).raw
      ),
    getScanners: async (): Promise<ScannersResponse> => {
      const result = await requestApi.fetchString("GET", `/scanners`);
      return asyncJsonParse<ScannersResponse>(result.raw);
    },
    connectTopicUpdates: (
      onUpdate: (topVersions: TopicVersions) => void
    ): (() => void) => {
      let timeoutId: ReturnType<typeof setTimeout> | undefined;
      let eventSource: EventSource | undefined;

      const connect = () => {
        eventSource = new EventSource(`${apiBaseUrl}/topics/stream`);
        eventSource.onmessage = (e) =>
          onUpdate(JSON.parse(e.data) as TopicVersions);
        eventSource.onerror = () => {
          eventSource?.close();
          timeoutId = setTimeout(connect, 5000);
        };
      };

      connect();
      return () => {
        clearTimeout(timeoutId);
        eventSource?.close();
      };
    },
    storage: NoPersistence,
  };
};
