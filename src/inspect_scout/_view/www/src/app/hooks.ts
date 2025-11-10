import { ColumnTable, fromArrow } from "arquero";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { getRelativePathFromParams, parseScanResultPath } from "../router/url";
import { useApi, useStore } from "../state/store";
import { EventType } from "../transcript/types";
import { Transcript, ModelUsage } from "../types";
import { JsonValue, Events } from "../types/log";
import { asyncJsonParse } from "../utils/json-worker";

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
  const setLoading = useStore((state) => state.setLoading);

  useEffect(() => {
    const fetchScans = async () => {
      setLoading(true);
      try {
        const scansInfo = await api.getScans();
        if (scansInfo) {
          setResultsDir(scansInfo.results_dir);
          setScans(scansInfo.scans);
        }
      } finally {
        setLoading(false);
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
  const setSelectedScanLocation = useStore(
    (state) => state.setSelectedScanLocation
  );
  const setLoading = useStore((state) => state.setLoading);
  const setSelectedResults = useStore((state) => state.setSelectedResults);
  const api = useApi();

  useEffect(() => {
    const fetchScan = async () => {
      setLoading(true);
      try {
        const scansInfo = await api.getScan(scanPath);
        if (scansInfo) {
          setSelectedResults(scansInfo);
        }
        setSelectedScanLocation(scanPath);
      } finally {
        setLoading(false);
      }
    };
    void fetchScan();
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
  const { data: scanData, isLoading } = useScannerData(scannerResults, scanResultUuid);
  return { data: scanData, isLoading };
};

export const useScannerData = (
  columnTable: ColumnTable,
  scanResultUuid?: string
) => {
  const [scannerData, setScannerData] = useState<ScannerData | undefined>(
    undefined
  );
  const [isLoading, setIsLoading] = useState(false);

  const filtered = useMemo(() => {
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

    return filtered;
  }, [columnTable, scanResultUuid]);

  useEffect(() => {
    if (!filtered) {
      setScannerData(undefined);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    setIsLoading(true);

    const parseData = async () => {
      try {
        const [
          eventReferences,
          input,
          inputIds,
          messageReferences,
          metadata,
          scanEvents,
          scanMetadata,
          scanModelUsage,
          scanTags,
          scannerParams,
          transcriptMetadata,
          validationResult,
          validationTarget,
        ] = await Promise.all([
          asyncJsonParse(filtered.get("event_references", 0) as string),
          asyncJsonParse(filtered.get("input", 0) as string),
          asyncJsonParse(filtered.get("input_ids", 0) as string),
          asyncJsonParse(filtered.get("message_references", 0) as string),
          asyncJsonParse(filtered.get("metadata", 0) as string),
          asyncJsonParse(filtered.get("scan_events", 0) as string),
          asyncJsonParse(filtered.get("scan_metadata", 0) as string),
          asyncJsonParse(filtered.get("scan_model_usage", 0) as string),
          asyncJsonParse(filtered.get("scan_tags", 0) as string),
          asyncJsonParse(filtered.get("scanner_params", 0) as string),
          asyncJsonParse(filtered.get("transcript_metadata", 0) as string),
          asyncJsonParse(filtered.get("validation_result", 0) as string),
          asyncJsonParse(filtered.get("validation_target", 0) as string),
        ]);

        if (cancelled) return;

        const uuid = filtered.get("uuid", 0) as string | undefined;
        const answer = filtered.get("answer", 0) as string | undefined;
        const explanation = filtered.get("explanation", 0) as
          | string
          | undefined;
        const inputType = filtered.get("input_type", 0) as
          | "transcript"
          | "message"
          | "messages"
          | "event"
          | "events";
        const scanError = filtered.get("scan_error", 0) as string | undefined;
        const scanErrorTraceback = filtered.get("scan_error_traceback", 0) as
          | string
          | undefined;
        const scanId = filtered.get("scan_id", 0) as string;
        const scanTotalTokens = filtered.get("scan_total_tokens", 0) as number;
        const scannerFile = filtered.get("scanner_file", 0) as string;
        const scannerKey = filtered.get("scanner_key", 0) as string;
        const scannerName = filtered.get("scanner_name", 0) as string;
        const transcriptId = filtered.get("transcript_id", 0) as string;
        const transcriptSourceId = filtered.get(
          "transcript_source_id",
          0
        ) as string;
        const transcriptSourceUri = filtered.get(
          "transcript_source_uri",
          0
        ) as string;
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

        const baseData = {
          uuid,
          answer,
          eventReferences: eventReferences as ScannerReference[],
          explanation,
          inputIds: inputIds as string[],
          messageReferences: messageReferences as ScannerReference[],
          metadata: metadata as Record<string, JsonValue>,
          scanError,
          scanErrorTraceback,
          scanEvents: scanEvents as Events,
          scanId,
          scanMetadata: scanMetadata as Record<string, JsonValue>,
          scanModelUsage: scanModelUsage as Record<string, ModelUsage>,
          scanTags: scanTags as string[],
          scanTotalTokens,
          scannerFile,
          scannerKey,
          scannerName,
          scannerParams: scannerParams as Record<string, JsonValue>,
          transcriptId,
          transcriptMetadata: transcriptMetadata as Record<string, JsonValue>,
          transcriptSourceId,
          transcriptSourceUri,
          validationResult: validationResult as
            | boolean
            | Record<string, boolean>,
          validationTarget: validationTarget as
            | boolean
            | Record<string, boolean>,
          value,
          valueType,
        };

        // Create typed data based on inputType
        let typedData: ScannerData;
        switch (inputType) {
          case "transcript":
            typedData = {
              ...baseData,
              inputType: "transcript",
              input: input as Transcript,
            };
            break;
          case "message":
            typedData = {
              ...baseData,
              inputType: "message",
              input: input as MessageType,
            };
            break;
          case "messages":
            typedData = {
              ...baseData,
              inputType: "messages",
              input: input as MessageType[],
            };
            break;
          case "event":
            typedData = {
              ...baseData,
              inputType: "event",
              input: input as EventType,
            };
            break;
          case "events":
            typedData = {
              ...baseData,
              inputType: "events",
              input: input as EventType[],
            };
            break;
        }

        setScannerData(typedData);
        setIsLoading(false);
      } catch (error) {
        if (!cancelled) {
          console.error("Error parsing scanner data:", error);
          setScannerData(undefined);
          setIsLoading(false);
        }
      }
    };

    void parseData();

    return () => {
      cancelled = true;
    };
  }, [filtered]);

  return { data: scannerData, isLoading };
};

export const useSelectedResultsRow = (scanResultUuid: string) => {
  const scannerResults = useScannerResults();
  const { data: scanData, isLoading } = useScannerData(scannerResults, scanResultUuid);
  return { data: scanData, isLoading };
};

export const useScannerPreviews = (columnTable: ColumnTable) => {
  const [scannerPreviews, setScannerPreviews] = useState<ScannerCore[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const rowData = useMemo(() => columnTable.objects(), [columnTable]);

  useEffect(() => {
    if (rowData.length === 0) {
      setScannerPreviews([]);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    setIsLoading(true);

    const parsePreviews = async () => {
      try {
        const parsedPreviews = await Promise.all(
          rowData.map(async (row) => {
            const r = row as Record<string, unknown>;

            const [
              validationResult,
              validationTarget,
              transcriptMetadata,
              eventReferences,
              messageReferences,
              input,
            ] = await Promise.all([
              asyncJsonParse(r.validation_result as string),
              asyncJsonParse(r.validation_target as string),
              asyncJsonParse(r.transcript_metadata as string),
              asyncJsonParse(r.event_references as string),
              asyncJsonParse(r.message_references as string),
              asyncJsonParse(r.input as string),
            ]);

            const explanation = r.explanation as string;
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
            const transcriptSourceId = r.transcript_source_id as string;
            const inputType = r.input_type as
              | "transcript"
              | "message"
              | "messages"
              | "event"
              | "events";

            const basePreview = {
              uuid: r.uuid as string | undefined,
              label: r.label as string | undefined,
              explanation,
              eventReferences: eventReferences as ScannerReference[],
              messageReferences: messageReferences as ScannerReference[],
              validationResult: validationResult as
                | boolean
                | Record<string, boolean>,
              validationTarget: validationTarget as
                | boolean
                | Record<string, boolean>,
              value,
              valueType,
              transcriptMetadata: transcriptMetadata as Record<string, JsonValue>,
              transcriptSourceId,
            };

            // Create typed preview based on inputType
            let typedPreview: ScannerCore;
            switch (inputType) {
              case "transcript":
                typedPreview = {
                  ...basePreview,
                  inputType: "transcript",
                  input: input as Transcript,
                };
                break;
              case "message":
                typedPreview = {
                  ...basePreview,
                  inputType: "message",
                  input: input as MessageType,
                };
                break;
              case "messages":
                typedPreview = {
                  ...basePreview,
                  inputType: "messages",
                  input: input as MessageType[],
                };
                break;
              case "event":
                typedPreview = {
                  ...basePreview,
                  inputType: "event",
                  input: input as EventType,
                };
                break;
              case "events":
                typedPreview = {
                  ...basePreview,
                  inputType: "events",
                  input: input as EventType[],
                };
                break;
            }

            return typedPreview;
          })
        );

        if (!cancelled) {
          setScannerPreviews(parsedPreviews);
          setIsLoading(false);
        }
      } catch (error) {
        if (!cancelled) {
          console.error("Error parsing scanner previews:", error);
          setScannerPreviews([]);
          setIsLoading(false);
        }
      }
    };

    void parsePreviews();

    return () => {
      cancelled = true;
    };
  }, [rowData]);

  return { data: scannerPreviews, isLoading };
};
