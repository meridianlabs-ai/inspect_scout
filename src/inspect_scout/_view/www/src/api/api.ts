import { StateStorage } from "zustand/middleware";

import { ScanResultInputData } from "../app/types";
import type { Condition, OrderByModel } from "../query";
import {
  AppConfig,
  Pagination,
  ScansResponse,
  Status,
  Transcript,
  TranscriptsResponse,
} from "../types/api-types";

export type ClientStorage = StateStorage;

export interface ScanApi {
  getConfig(): Promise<AppConfig>;
  getTranscripts(
    transcriptsDir: string,
    filter?: Condition,
    orderBy?: OrderByModel | OrderByModel[],
    pagination?: Pagination
  ): Promise<TranscriptsResponse>;
  getTranscript(transcriptsDir: string, id: string): Promise<Transcript>;
  getScans(
    filter?: Condition,
    orderBy?: OrderByModel | OrderByModel[],
    pagination?: Pagination
  ): Promise<ScansResponse>;
  getScan(scanLocation: string): Promise<Status>;
  getScannerDataframe(
    scanLocation: string,
    scanner: string
  ): Promise<ArrayBuffer | Uint8Array>;
  getScannerDataframeInput(
    scanLocation: string,
    scanner: string,
    uuid: string
  ): Promise<ScanResultInputData>;

  storage: ClientStorage;
  capability: "scans" | "workbench";
}

export const NoPersistence: ClientStorage = {
  getItem: (_name: string): string | null => {
    return null;
  },
  setItem: (_name: string, _value: string): void => {},
  removeItem: (_name: string): void => {},
};
