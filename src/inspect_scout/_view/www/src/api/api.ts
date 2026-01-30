import { StateStorage } from "zustand/middleware";

import { ScanResultInputData } from "../app/types";
import type { Condition, OrderByModel } from "../query";
import {
  ActiveScansResponse,
  AppConfig,
  CreateValidationSetRequest,
  InvalidationTopic,
  Pagination,
  ProjectConfig,
  ProjectConfigInput,
  ScanJobConfig,
  ScannersResponse,
  ScansResponse,
  Status,
  Transcript,
  TranscriptsResponse,
  ValidationCase,
  ValidationCaseRequest,
} from "../types/api-types";

export type ClientStorage = StateStorage;

export type ScalarValue = string | number | boolean | null;

/** Topic versions: maps topic name to timestamp. */
export type TopicVersions = Record<InvalidationTopic, string>;

export interface ScanApi {
  getConfig(): Promise<AppConfig>;
  getTranscripts(
    transcriptsDir: string,
    filter?: Condition,
    orderBy?: OrderByModel | OrderByModel[],
    pagination?: Pagination
  ): Promise<TranscriptsResponse>;
  hasTranscript(transcriptsDir: string, id: string): Promise<boolean>;
  getTranscript(transcriptsDir: string, id: string): Promise<Transcript>;
  getTranscriptsColumnValues(
    transcriptsDir: string,
    column: string,
    filter: Condition | undefined
  ): Promise<ScalarValue[]>;
  getScans(
    scansDir: string,
    filter?: Condition,
    orderBy?: OrderByModel | OrderByModel[],
    pagination?: Pagination
  ): Promise<ScansResponse>;
  getScansColumnValues(
    scansDir: string,
    column: string,
    filter: Condition | undefined
  ): Promise<ScalarValue[]>;
  getScan(scansDir: string, scanPath: string): Promise<Status>;
  getScannerDataframe(
    scansDir: string,
    scanPath: string,
    scanner: string
  ): Promise<ArrayBuffer | Uint8Array>;
  getScannerDataframeInput(
    scansDir: string,
    scanPath: string,
    scanner: string,
    uuid: string
  ): Promise<ScanResultInputData>;
  getActiveScans(): Promise<ActiveScansResponse>;
  postCode(condition: Condition): Promise<Record<string, string>>;
  getProjectConfig(): Promise<{ config: ProjectConfig; etag: string }>;
  updateProjectConfig(
    config: ProjectConfigInput,
    etag: string | null
  ): Promise<{ config: ProjectConfig; etag: string }>;
  startScan(config: ScanJobConfig): Promise<Status>;
  getScanners(): Promise<ScannersResponse>;
  connectTopicUpdates(
    onUpdate: (topVersions: TopicVersions) => void
  ): () => void;

  // Validation API
  getValidationSets(): Promise<string[]>;
  getValidationCases(uri: string): Promise<ValidationCase[]>;
  getValidationCase(uri: string, caseId: string): Promise<ValidationCase>;
  createValidationSet(request: CreateValidationSetRequest): Promise<string>;
  upsertValidationCase(
    uri: string,
    caseId: string,
    data: ValidationCaseRequest
  ): Promise<ValidationCase>;
  deleteValidationCase(uri: string, caseId: string): Promise<boolean>;
  deleteValidationSet(uri: string): Promise<boolean>;
  renameValidationSet(uri: string, newName: string): Promise<string>;

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
