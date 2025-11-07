import { ColumnTable, fromArrow } from "arquero";
import { use, useEffect, useMemo } from "react";
import { useParams } from "react-router-dom";

import { getRelativePathFromParams } from "../router/url";
import { useStore } from "../state/store";
import { EventType } from "../transcript/types";
import { Transcript, ModelUsage } from "../types";
import { JsonValue, Events } from "../types/log";

import {
  MessageType,
  ScannerData,
  ScannerPreview,
  ScannerReference,
} from "./types";

export const useSelectedScanner = () => {
  const selectedScanner = useStore((state) => state.selectedScanner);
  const selectedResults = useStore((state) => state.selectedResults);
  const defaultScanner = useMemo(() => {
    if (selectedResults) {
      const scanners = Object.keys(selectedResults.summary.scanners);
      return scanners.length > 0 ? scanners[0] : undefined;
    }
  }, [selectedResults]);

  return selectedScanner || defaultScanner;
};

export const useServerScans = () => {
  const api = useStore((state) => state.api);
  const setScans = useStore((state) => state.setScans);
  const setResultsDir = useStore((state) => state.setResultsDir);

  useEffect(() => {
    const fetchScans = async () => {
      const scansInfo = await api?.getScans();
      if (scansInfo) {
        setResultsDir(scansInfo.results_dir);
        setScans(scansInfo.scans);
      }
    };
    void fetchScans();
  }, [api, setScans, setResultsDir]);
};

export const useServerScanner = () => {
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);

  const setSelectedScan = useStore((state) => state.setSelectedResults);
  const api = useStore((state) => state.api);

  useEffect(() => {
    const fetchScans = async () => {
      const scansInfo = await api?.getScan(relativePath);
      if (scansInfo) {
        setSelectedScan(scansInfo);
      }
    };
    void fetchScans();
  }, [relativePath, api, setSelectedScan]);
};

export const useScannerResults = () => {
  const selectedScanner = useSelectedScanner();
  const selectedResults = useStore((state) => state.selectedResults);
  const scanner = selectedResults?.scanners[selectedScanner || ""];
  const columnTable = useMemo(() => {
    if (!scanner || !scanner.data) {
      return fromArrow(new ArrayBuffer(0));
    }

    // Decode base64 string to Uint8Array
    const binaryString = atob(scanner.data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    // Load Arrow data using Arquero
    const table = fromArrow(bytes.buffer);
    return table;
  }, [scanner]);
  return columnTable;
};

export const useScannerResult = (scanResultUuid: string) => {
  const scannerResults = useScannerResults();

  const row = useMemo(() => {
    const rowData = scannerResults.objects();
    const row = rowData.findIndex((r) => {
      return (r as Record<string, string>).uuid === scanResultUuid;
    });
    return row;
  }, [scannerResults, scanResultUuid]);

  const scanData = useScannerData(row, scannerResults);
  return scanData;
};

export const useScannerData = (row: number, columnTable: ColumnTable) => {
  const scannerSummaries = useMemo(() => {
    const rowData = columnTable.objects();
    // Not a valid index
    if (row === -1) {
      return undefined;
    }

    // Out of bounds
    if (row > rowData.length - 1) {
      return undefined;
    }

    const r = rowData[row] as Record<string, unknown>;
    const uuid = r.uuid as string | undefined;

    const answer = r.answer as string | undefined;
    const eventReferences = JSON.parse(
      r.event_references as string
    ) as ScannerReference[];
    const explanation = r.explanation as string | undefined;

    const input = JSON.parse(r.input as string) as
      | Transcript
      | MessageType
      | MessageType[]
      | EventType
      | EventType[];
    const inputIds = JSON.parse(r.input_ids as string) as string[];
    const inputType = r.input_type as
      | "transcript"
      | "message"
      | "messages"
      | "event"
      | "events";
    const messageReferences = JSON.parse(
      r.message_references as string
    ) as ScannerReference[];
    const metadata = JSON.parse(r.metadata as string) as Record<
      string,
      JsonValue
    >;

    const scanError = r.scan_error as string | undefined;
    const scanErrorTraceback = r.scan_error_traceback as string | undefined;
    const scanEvents = JSON.parse(r.scan_events as string) as Events;
    const scanId = r.scan_id as string;
    const scanMetdata = JSON.parse(r.scan_metadata as string) as Record<
      string,
      JsonValue
    >;
    const scanModelUsage = JSON.parse(r.scan_model_usage as string) as Record<
      string,
      ModelUsage
    >;
    const scanTags = JSON.parse(r.scan_tags as string) as string[];
    const scanTotalTokens = r.scan_total_tokens as number;
    const scannerFile = r.scanner_file as string;
    const scannerKey = r.scanner_key as string;
    const scannerName = r.scanner_name as string;
    const scannerParams = JSON.parse(r.scanner_params as string) as Record<
      string,
      JsonValue
    >;
    const timestamp = new Date(r.timestamp as string);

    const transcriptId = r.transcript_id as string;
    const transcriptMetadata = JSON.parse(
      r.transcript_metadata as string
    ) as Record<string, JsonValue>;
    const transcriptSourceId = r.transcript_source_id as string;
    const transcriptSourceUri = r.transcript_source_uri as string;

    const validationResult = JSON.parse(r.validation_result as string) as
      | boolean
      | Record<string, boolean>;
    const validationTarget = JSON.parse(r.validation_target as string) as
      | boolean
      | Record<string, boolean>;

    const value = r.value as
      | string
      | boolean
      | number
      | null
      | unknown[]
      | object;
    const valueType = r.value_type as
      | "string"
      | "number"
      | "boolean"
      | "null"
      | "array"
      | "object";

    return {
      uuid,
      answer,
      eventReferences,
      explanation,
      input,
      inputIds,
      inputType,
      messageReferences,
      metadata,
      scanError,
      scanErrorTraceback,
      scanEvents,
      scanId,
      scanMetdata,
      scanModelUsage,
      scanTags,
      scanTotalTokens,
      scannerFile,
      scannerKey,
      scannerName,
      scannerParams,
      timestamp,
      transcriptId,
      transcriptMetadata,
      transcriptSourceId,
      transcriptSourceUri,
      validationResult,
      validationTarget,
      value,
      valueType,
    } as ScannerData;
  }, [columnTable, row]);
  return scannerSummaries;
};

export const useSelectedResultsRow = (scanResultUuid: string) => {
  const scannerResults = useScannerResults();
  const row = useMemo(() => {
    const rowData = scannerResults.objects();
    const row = rowData.findIndex((r) => {
      return (r as Record<string, string>).uuid === scanResultUuid;
    });
    return row;
  }, [scannerResults, scanResultUuid]);

  const scanData = useScannerData(row, scannerResults);
  return scanData;
};

export const useScannerPreviews = (columnTable: ColumnTable) => {
  const scannerPreviews = useMemo(() => {
    const rowData = columnTable.objects();
    const previews: ScannerPreview[] = rowData.map((row) => {
      const r = row as Record<string, unknown>;

      const explanation = r.explanation as string;
      const validationResult = JSON.parse(r.validation_result as string) as
        | boolean
        | Record<string, boolean>;
      const validationTarget = JSON.parse(r.validation_target as string) as
        | boolean
        | Record<string, boolean>;

      const value = r.value as
        | string
        | boolean
        | number
        | null
        | unknown[]
        | object;
      const valueType = r.value_type as
        | "string"
        | "number"
        | "boolean"
        | "null"
        | "array"
        | "object";

      const transcriptMetadata = JSON.parse(
        r.transcript_metadata as string
      ) as Record<string, JsonValue>;

      const transcriptSourceId = r.transcript_source_id as string;

      return {
        uuid: r.uuid as string | undefined,
        label: r.label as string | undefined,
        explanation,
        type: r.input_type,
        validationResult,
        validationTarget,
        value,
        valueType,
        transcriptMetadata,
        transcriptSourceId,
      } as ScannerPreview;
    });
    return previews;
  }, [columnTable]);
  return scannerPreviews;
};
