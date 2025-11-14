import { ColumnTable } from "arquero";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { getRelativePathFromParams, parseScanResultPath } from "../router/url";
import { useApi, useStore } from "../state/store";
import { EventType } from "../transcript/types";
import { Transcript, ModelUsage } from "../types";
import { JsonValue, Events } from "../types/log";
import { decodeArrowBytes } from "../utils/arrow";
import { asyncJsonParse } from "../utils/json-worker";
import { join } from "../utils/uri";

import {
  MessageType,
  ScannerData,
  ScannerCore,
  ScannerReference,
} from "./types";
import { expandResultsetRows } from "./utils/arrow";

export const useSelectedScanner = () => {
  const selectedScanner = useStore((state) => state.selectedScanner);
  const selectedStatus = useStore((state) => state.selectedScanStatus);
  const defaultScanner = useMemo(() => {
    if (selectedStatus) {
      const scanners = Object.keys(selectedStatus.summary.scanners);
      return scanners.length > 0 ? scanners[0] : undefined;
    }
  }, [selectedStatus, selectedStatus?.summary.scanners]);

  return selectedScanner || defaultScanner;
};

export const useServerScans = () => {
  // api
  const api = useApi();

  // state
  const resultsDir = useStore((state) => state.resultsDir);

  // setters
  const setScans = useStore((state) => state.setScans);
  const setResultsDir = useStore((state) => state.setResultsDir);
  const setLoading = useStore((state) => state.setLoading);
  const setError = useStore((state) => state.setError);
  const clearError = useStore((state) => state.clearError);

  useEffect(() => {
    const fetchScans = async () => {
      // Update loading and error state
      clearError("scanjobs");
      setLoading(true);

      try {
        // Fetch the data
        const scansInfo = await api.getScans();
        if (scansInfo) {
          // Update state
          setResultsDir(scansInfo.results_dir);
          setScans(scansInfo.scans);
        }
      } catch (e) {
        // Notify app of error
        setError("scanjobs", e?.toString());
      } finally {
        // Stop loading
        setLoading(false);
      }
    };

    // Only fetch if we don't already have data retrieved
    if (!resultsDir) {
      void fetchScans();
    }
  }, [api, resultsDir, setScans, setResultsDir]);
};

export const useServerScannerDataframe = () => {
  // api
  const api = useApi();

  // Path information
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);
  const { scanPath } = parseScanResultPath(relativePath);

  // State
  const singleFileMode = useStore((state) => state.singleFileMode);
  const resultsDir = useStore((state) => state.resultsDir);
  const selectedScanner = useSelectedScanner();

  // Setters
  const setLoadingData = useStore((state) => state.setLoadingData);
  const setSelectedScanResultData = useStore(
    (state) => state.setSelectedScanResultData
  );
  const getSelectedScanResultData = useStore(
    (state) => state.getSelectedScanResultData
  );
  const setError = useStore((state) => state.setError);
  const clearError = useStore((state) => state.clearError);

  useEffect(() => {
    const fetchScannerDataframe = async () => {
      // Clear any existing errors
      clearError("dataframe");

      // See if we already have data
      const existingData = getSelectedScanResultData(selectedScanner);
      if (!scanPath || !selectedScanner || existingData) {
        return;
      }

      // Start loading (since we are going to fetch)
      setLoadingData(true);
      try {
        // In single file mode, send an absolute path
        let location = scanPath;
        if (singleFileMode) {
          location = join(scanPath, resultsDir);
        }

        // Request the raw data from the server
        const arrayBuffer = await api.getScannerDataframe(
          location,
          selectedScanner
        );

        // Pre-process result set rows to explode the results
        const table = decodeArrowBytes(arrayBuffer);
        const expandedTable = expandResultsetRows(table);

        // Store in state
        setSelectedScanResultData(selectedScanner, expandedTable);
      } catch (e) {
        // Notify app of error
        setError("dataframe", e?.toString());
      } finally {
        // Stop progress
        setLoadingData(false);
      }
    };
    void fetchScannerDataframe();
  }, [
    api,
    scanPath,
    selectedScanner,
    resultsDir,
    singleFileMode,
    setLoadingData,
    setSelectedScanResultData,
    getSelectedScanResultData,
  ]);
};

export const useServerScanner = () => {
  // api
  const api = useApi();

  // Path information
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);
  const { scanPath } = parseScanResultPath(relativePath);

  // State
  const resultsDir = useStore((state) => state.resultsDir);
  const selectedStatus = useStore((state) => state.selectedScanStatus);
  const scans = useStore((state) => state.scans);

  // Setters
  const setSelectedScanLocation = useStore(
    (state) => state.setSelectedScanLocation
  );
  const setSelectedScanStatus = useStore(
    (state) => state.setSelectedScanStatus
  );
  const setLoading = useStore((state) => state.setLoading);
  const setError = useStore((state) => state.setError);
  const clearError = useStore((state) => state.clearError);

  useEffect(() => {
    if (scanPath && !selectedStatus) {
      // Clear any existing errors
      clearError("scanner");

      // Check the list of scans that are already loaded
      const location = join(scanPath, resultsDir);
      const scansInfo = scans.find((s) => s.location === location);
      if (scansInfo) {
        // Already in store, use it
        setSelectedScanStatus(scansInfo);
      } else {
        // Fetch from server if not in store
        const fetchScan = async () => {
          setLoading(true);
          try {
            const status = await api.getScan(location);
            setSelectedScanStatus(status);
          } catch (e) {
            setError("scanner", e?.toString());
          } finally {
            setLoading(false);
          }
        };
        void fetchScan();
      }

      // Select this scan
      setSelectedScanLocation(scanPath);
    }
  }, [
    relativePath,
    api,
    setSelectedScanStatus,
    scanPath,
    selectedStatus,
    scans,
    resultsDir,
  ]);
};

export const useScannerData = (
  columnTable?: ColumnTable,
  scanResultUuid?: string
) => {
  const [scannerData, setScannerData] = useState<ScannerData | undefined>(
    undefined
  );
  const [isLoading, setIsLoading] = useState(false);

  const filtered = useMemo(() => {
    // Not a valid index
    if (!scanResultUuid || !columnTable) {
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
        const valueType = filtered.get("value_type", 0) as
          | "string"
          | "number"
          | "boolean"
          | "null"
          | "array"
          | "object";

        const simpleValue = (
          val: unknown,
          valueType:
            | "string"
            | "number"
            | "boolean"
            | "null"
            | "array"
            | "object"
        ): Promise<string | number | boolean | null | unknown[] | object> => {
          if (valueType === "object" || valueType === "array") {
            return asyncJsonParse<object | unknown[]>(val as string);
          } else {
            return Promise.resolve(val as string | number | boolean | null);
          }
        };

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
          value,
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
          simpleValue(filtered.get("value", 0), valueType),
        ]);

        if (cancelled) return;

        const uuid = filtered.get("uuid", 0) as string | undefined;
        const answer = filtered.get("answer", 0) as string | undefined;
        const label = filtered.columnNames().includes("label")
          ? (filtered.get("label", 0) as string | undefined)
          : undefined;
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

        const baseData = {
          uuid,
          answer,
          label,
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

export const useSelectedResultsRow = (scanResultUuid?: string) => {
  const getSelectedScanResultData = useStore(
    (state) => state.getSelectedScanResultData
  );

  // Get the column data for the selected scanner
  const selectedScanner = useSelectedScanner();
  const selectedScanResultData = getSelectedScanResultData(selectedScanner);

  const { data: scanData, isLoading } = useScannerData(
    selectedScanResultData,
    scanResultUuid
  );
  return { data: scanData, isLoading };
};

export const useScannerPreviews = (columnTable?: ColumnTable) => {
  // First see if we've already decoded these
  const selectedScanner = useSelectedScanner();
  const getSelectedScanResultPreviews = useStore(
    (state) => state.getSelectedScanResultPreviews
  );
  const setSelectedScanResultPreviews = useStore(
    (state) => state.setSelectedScanResultPreviews
  );

  const [scannerPreviews, setScannerPreviews] = useState<ScannerCore[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const rowData = useMemo(() => columnTable?.objects(), [columnTable]);

  useEffect(() => {
    // If empty, set empty and return
    if (rowData?.length === 0) {
      setScannerPreviews([]);
      setSelectedScanResultPreviews(selectedScanner, []);
      setIsLoading(false);
      return;
    }

    // Use the existing previews if available
    const existingPreviews = getSelectedScanResultPreviews(selectedScanner);
    if (existingPreviews) {
      setScannerPreviews(existingPreviews);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    setIsLoading(true);

    const parsePreviews = async () => {
      try {
        const parsedPreviews = await Promise.all(
          (rowData || []).map(async (row) => {
            const r = row as Record<string, unknown>;

            // Determine the value type
            const valueType = r.value_type as
              | "string"
              | "number"
              | "boolean"
              | "null"
              | "array"
              | "object";

            const simpleValue = (
              val: unknown,
              valueType:
                | "string"
                | "number"
                | "boolean"
                | "null"
                | "array"
                | "object"
            ): Promise<
              string | number | boolean | null | unknown[] | object
            > => {
              if (valueType === "object" || valueType === "array") {
                return asyncJsonParse<object | unknown[]>(val as string);
              } else {
                return Promise.resolve(val as string | number | boolean | null);
              }
            };
            const [
              validationResult,
              validationTarget,
              transcriptMetadata,
              eventReferences,
              messageReferences,
              input,
              value,
            ] = await Promise.all([
              asyncJsonParse(r.validation_result as string),
              asyncJsonParse(r.validation_target as string),
              asyncJsonParse<Record<string, unknown>>(
                r.transcript_metadata as string
              ),
              asyncJsonParse(r.event_references as string),
              asyncJsonParse(r.message_references as string),
              asyncJsonParse(r.input as string),
              simpleValue(r.value, valueType),
            ]);

            const explanation = r.explanation as string;
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
              transcriptMetadata,
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
          setSelectedScanResultPreviews(selectedScanner, parsedPreviews);
          setIsLoading(false);
        }
      } catch (error) {
        if (!cancelled) {
          console.error("Error parsing scanner previews:", error);
          setScannerPreviews([]);
          setSelectedScanResultPreviews(selectedScanner, []);
          setIsLoading(false);
        }
      }
    };

    void parsePreviews();

    return () => {
      cancelled = true;
    };
  }, [
    rowData,
    selectedScanner,
    getSelectedScanResultPreviews,
    setSelectedScanResultPreviews,
  ]);

  return { data: scannerPreviews, isLoading };
};
