import { ColumnTable, fromArrow } from "arquero";
import { useEffect, useMemo } from "react";
import { useParams } from "react-router-dom";

import { getRelativePathFromParams, parseScanResultPath } from "../router/url";
import { useApi, useStore } from "../state/store";
import { EventType } from "../transcript/types";
import { Transcript, ModelUsage } from "../types";
import { JsonValue, Events } from "../types/log";

import {
  MessageType,
  ScannerData,
  ScannerCore,
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
  const api = useApi();
  const setScans = useStore((state) => state.setScans);
  const setResultsDir = useStore((state) => state.setResultsDir);
  const resultsDir = useStore((state) => state.resultsDir);

  useEffect(() => {
    const fetchScans = async () => {
      const scansInfo = await api.getScans();
      if (scansInfo) {
        setResultsDir(scansInfo.results_dir);
        setScans(scansInfo.scans);
      }
    };
    if (!resultsDir) {
      void fetchScans();
    }
  }, [api, resultsDir, setScans, setResultsDir]);
};

export const useServerScanner = () => {
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);
  const { scanPath } = parseScanResultPath(relativePath);

  const setSelectedResults = useStore((state) => state.setSelectedResults);
  const api = useApi();

  useEffect(() => {
    const fetchScans = async () => {
      const scansInfo = await api.getScan(scanPath);
      if (scansInfo) {
        setSelectedResults(scansInfo);
      }
    };
    void fetchScans();
  }, [relativePath, api, setSelectedResults, scanPath]);
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
  const scanData = useScannerData(scannerResults, scanResultUuid);
  return scanData;
};

export const useScannerData = (
  columnTable: ColumnTable,
  scanResultUuid?: string
) => {
  const scannerSummaries = useMemo(() => {
    // Not a valid index
    if (!scanResultUuid) {
      return undefined;
    }

    // Empty table
    if (columnTable.columnNames().length === 0) {
      return undefined;
    }
    const filtered = columnTable
      .params({ targetUuid: scanResultUuid })
      .filter(
        (d: { uuid: string }, $: { targetUuid: string }) =>
          d.uuid === $.targetUuid
      );

    if (filtered.numRows() === 0) {
      return undefined;
    }

    const uuid = filtered.get("uuid", 0) as string | undefined;
    const answer = filtered.get("answer", 0) as string | undefined;
    const eventReferences = JSON.parse(
      filtered.get("event_references", 0) as string
    ) as ScannerReference[];
    const explanation = filtered.get("explanation", 0) as string | undefined;

    const input = JSON.parse(filtered.get("input", 0) as string) as
      | Transcript
      | MessageType
      | MessageType[]
      | EventType
      | EventType[];
    const inputIds = JSON.parse(
      filtered.get("input_ids", 0) as string
    ) as string[];
    const inputType = filtered.get("input_type", 0) as
      | "transcript"
      | "message"
      | "messages"
      | "event"
      | "events";
    const messageReferences = JSON.parse(
      filtered.get("message_references", 0) as string
    ) as ScannerReference[];
    const metadata = JSON.parse(
      filtered.get("metadata", 0) as string
    ) as Record<string, JsonValue>;

    const scanError = filtered.get("scan_error", 0) as string | undefined;
    const scanErrorTraceback = filtered.get("scan_error_traceback", 0) as
      | string
      | undefined;
    const scanEvents = JSON.parse(
      filtered.get("scan_events", 0) as string
    ) as Events;
    const scanId = filtered.get("scan_id", 0) as string;
    const scanMetadata = JSON.parse(
      filtered.get("scan_metadata", 0) as string
    ) as Record<string, JsonValue>;
    const scanModelUsage = JSON.parse(
      filtered.get("scan_model_usage", 0) as string
    ) as Record<string, ModelUsage>;
    const scanTags = JSON.parse(
      filtered.get("scan_tags", 0) as string
    ) as string[];
    const scanTotalTokens = filtered.get("scan_total_tokens", 0) as number;
    const scannerFile = filtered.get("scanner_file", 0) as string;
    const scannerKey = filtered.get("scanner_key", 0) as string;
    const scannerName = filtered.get("scanner_name", 0) as string;
    const scannerParams = JSON.parse(
      filtered.get("scanner_params", 0) as string
    ) as Record<string, JsonValue>;

    const transcriptId = filtered.get("transcript_id", 0) as string;
    const transcriptMetadata = JSON.parse(
      filtered.get("transcript_metadata", 0) as string
    ) as Record<string, JsonValue>;
    const transcriptSourceId = filtered.get(
      "transcript_source_id",
      0
    ) as string;
    const transcriptSourceUri = filtered.get(
      "transcript_source_uri",
      0
    ) as string;

    const validationResult = JSON.parse(
      filtered.get("validation_result", 0) as string
    ) as boolean | Record<string, boolean>;
    const validationTarget = JSON.parse(
      filtered.get("validation_target", 0) as string
    ) as boolean | Record<string, boolean>;

    const value = filtered.get("value", 0) as
      | string
      | boolean
      | number
      | null
      | unknown[]
      | object;
    const valueType = filtered.get("value_type", 0) as
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
      scanMetadata,
      scanModelUsage,
      scanTags,
      scanTotalTokens,
      scannerFile,
      scannerKey,
      scannerName,
      scannerParams,
      transcriptId,
      transcriptMetadata,
      transcriptSourceId,
      transcriptSourceUri,
      validationResult,
      validationTarget,
      value,
      valueType,
    } as ScannerData;
  }, [columnTable, scanResultUuid]);
  return scannerSummaries;
};

export const useSelectedResultsRow = (scanResultUuid: string) => {
  const scannerResults = useScannerResults();

  const scanData = useScannerData(scannerResults, scanResultUuid);
  return scanData;
};

export const useScannerPreviews = (columnTable: ColumnTable) => {
  const scannerPreviews = useMemo(() => {
    const rowData = columnTable.objects();
    const previews: ScannerCore[] = rowData.map((row) => {
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
        inputType: r.input_type,
        validationResult,
        validationTarget,
        value,
        valueType,
        transcriptMetadata,
        transcriptSourceId,
      } as ScannerCore;
    });
    return previews;
  }, [columnTable]);
  return scannerPreviews;
};
