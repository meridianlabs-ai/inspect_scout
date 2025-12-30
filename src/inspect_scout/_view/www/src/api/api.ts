import { StateStorage } from "zustand/middleware";

import { ScanResultInputData } from "../app/types";
import type { Condition, OrderByModel } from "../query";
import { Status } from "../types";
import {
  Pagination,
  Transcript,
  TranscriptsResponse,
} from "../types/api-types";

export type ClientStorage = StateStorage;

export interface ScanApi {
  getTranscriptsDir(): Promise<string>;
  getTranscripts(
    transcriptsDir: string,
    filter?: Condition,
    orderBy?: OrderByModel | OrderByModel[],
    pagination?: Pagination
  ): Promise<TranscriptsResponse>;
  getTranscript(transcriptsDir: string, id: string): Promise<Transcript>;
  getScansDir(): Promise<string>;
  getScans(scansDir?: string): Promise<Status[]>;
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
