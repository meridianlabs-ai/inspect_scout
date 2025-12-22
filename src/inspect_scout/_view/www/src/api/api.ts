import { StateStorage } from "zustand/middleware";

import { ScanResultInputData } from "../app/types";
import { Status } from "../types";

export type ClientStorage = StateStorage;

export interface ScanApi {
  getTranscriptsDir(): Promise<string>;
  getTranscripts(transcriptsDir?: string): Promise<unknown[]>;
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
}

export const NoPersistence: ClientStorage = {
  getItem: (_name: string): string | null => {
    return null;
  },
  setItem: (_name: string, _value: string): void => {},
  removeItem: (_name: string): void => {},
};
