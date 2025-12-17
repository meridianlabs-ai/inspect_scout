import { ColumnTable } from "arquero";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { getRelativePathFromParams, parseScanResultPath } from "../router/url";
import { useStore } from "../state/store";
import { ModelUsage } from "../types";
import { JsonValue, Events } from "../types/log";
import { asyncJsonParse } from "../utils/json-worker";

import {
  ScanResultData,
  ScanResultSummary,
  ScanResultReference,
  ScanResultInputData,
} from "./types";

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

export const useSelectedScanResultData = (scanResultUuid?: string) => {
  const getSelectedScanResultData = useStore(
    (state) => state.getSelectedScanResultData
  );

  // Get the column data for the selected scanner
  const selectedScanner = useSelectedScanner();
  const selectedScanResultData = getSelectedScanResultData(selectedScanner);

  const { data: scanData, isLoading } = useScanResultData(
    selectedScanResultData,
    scanResultUuid
  );
  return { data: scanData, isLoading };
};

export const useSelectedScanResultInputData = ():
  | ScanResultInputData
  | undefined => {
  const params = useParams<{ "*": string }>();
  const relativePath = getRelativePathFromParams(params);
  const { scanResultUuid } = parseScanResultPath(relativePath);

  const getSelectedScanResultInput = useStore(
    (state) => state.getSelectedScanResultInputData
  );

  return scanResultUuid
    ? getSelectedScanResultInput(scanResultUuid)
    : undefined;
};

export const useScanResultSummaries = (columnTable?: ColumnTable) => {
  // First see if we've already decoded these
  const selectedScanner = useSelectedScanner();
  const getSelectedScanResultSummaries = useStore(
    (state) => state.getSelectedScanResultSummaries
  );
  const setSelectedScanResultSummaries = useStore(
    (state) => state.setSelectedScanResultSummaries
  );

  const [scanResultSummaries, setScanResultsSummaries] = useState<
    ScanResultSummary[]
  >([]);
  const [isLoading, setIsLoading] = useState(false);

  const rowData = useMemo(() => columnTable?.objects(), [columnTable]);

  useEffect(() => {
    // If empty, set empty and return
    if (rowData?.length === 0) {
      setScanResultsSummaries([]);
      setSelectedScanResultSummaries(selectedScanner, []);
      setIsLoading(false);
      return;
    }

    // Use the existing previews if available
    const existingPreviews = getSelectedScanResultSummaries(selectedScanner);
    if (existingPreviews) {
      setScanResultsSummaries(existingPreviews);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    setIsLoading(true);

    const jsonParse = async <T>(
      text: string | null
    ): Promise<T | undefined> => {
      return text !== null
        ? (asyncJsonParse<ScanResultSummary[]>(text) as Promise<T>)
        : undefined;
    };

    const parseScanResultSummaries = async () => {
      try {
        const parsedSummaries = await Promise.all(
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

            const simpleValue = async (
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
                return (
                  (await jsonParse<object | unknown[]>(val as string)) || null
                );
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
              value,
            ] = await Promise.all([
              jsonParse(r.validation_result as string),
              jsonParse(r.validation_target as string),
              jsonParse<Record<string, unknown>>(
                r.transcript_metadata as string
              ),
              jsonParse(r.event_references as string),
              jsonParse(r.message_references as string),
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

            const scanError = r.scan_error as string;
            const scanErrorRefusal = r.scan_error_refusal as boolean;
            const timestamp = r.timestamp
              ? new Date(r.timestamp as string)
              : undefined;

            const transcriptTaskSet = r.transcript_task_set as
              | string
              | undefined;

            const transcriptTaskId = r.transcript_task_id as
              | string
              | number
              | undefined;

            const transcriptTaskRepeat = r.transcript_task_repeat as
              | number
              | undefined;

            const baseSummary = {
              uuid: r.uuid as string | undefined,
              label: r.label as string | undefined,
              explanation,
              eventReferences: eventReferences as ScanResultReference[],
              messageReferences: messageReferences as ScanResultReference[],
              validationResult: validationResult as
                | boolean
                | Record<string, boolean>,
              validationTarget: validationTarget as
                | boolean
                | Record<string, boolean>,
              value,
              valueType,
              transcriptTaskSet,
              transcriptTaskId,
              transcriptTaskRepeat,
              transcriptMetadata: transcriptMetadata || {},
              transcriptSourceId,
              scanError,
              scanErrorRefusal,
              timestamp,
            };

            // Create typed preview based on inputType
            let typedSummary: ScanResultSummary;
            switch (inputType) {
              case "transcript":
                typedSummary = {
                  ...baseSummary,
                  inputType: "transcript",
                };
                break;
              case "message":
                typedSummary = {
                  ...baseSummary,
                  inputType: "message",
                };
                break;
              case "messages":
                typedSummary = {
                  ...baseSummary,
                  inputType: "messages",
                };
                break;
              case "event":
                typedSummary = {
                  ...baseSummary,
                  inputType: "event",
                };
                break;
              case "events":
                typedSummary = {
                  ...baseSummary,
                  inputType: "events",
                };
                break;
            }

            return typedSummary;
          })
        );

        if (!cancelled) {
          setScanResultsSummaries(parsedSummaries);
          setSelectedScanResultSummaries(selectedScanner, parsedSummaries);
          setIsLoading(false);
        }
      } catch (error) {
        if (!cancelled) {
          console.error("Error parsing scanner previews:", error);
          setScanResultsSummaries([]);
          setSelectedScanResultSummaries(selectedScanner, []);
          setIsLoading(false);
        }
      }
    };

    void parseScanResultSummaries();

    return () => {
      cancelled = true;
    };
  }, [
    rowData,
    selectedScanner,
    getSelectedScanResultSummaries,
    setSelectedScanResultSummaries,
  ]);

  return { data: scanResultSummaries, isLoading };
};

export const useScanResultData = (
  columnTable?: ColumnTable,
  scanResultUuid?: string
) => {
  const [scanResultData, setScanResultData] = useState<
    ScanResultData | undefined
  >(undefined);
  const [isLoading, setIsLoading] = useState(false);

  const filtered = useMemo((): ColumnTable | undefined => {
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
      setScanResultData(undefined);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    setIsLoading(true);

    const parse = async <T>(text: string | null): Promise<T | undefined> => {
      return text !== null
        ? (asyncJsonParse<ScanResultSummary[]>(text) as Promise<T>)
        : undefined;
    };

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
        ): Promise<
          string | number | boolean | null | unknown[] | object | undefined
        > => {
          if (valueType === "object" || valueType === "array") {
            return parse<object | unknown[]>(val as string);
          } else {
            return Promise.resolve(val as string | number | boolean | null);
          }
        };

        const transcript_agent_args_raw = getOptionalColumn<string>(
          filtered,
          "transcript_agent_args",
          0
        );
        const transcript_score_raw = getOptionalColumn<string>(
          filtered,
          "transcript_score",
          0
        );

        const [
          eventReferences,
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
          transcriptAgentArgs,
          transcriptScore,
        ] = await Promise.all([
          parse(filtered.get("event_references", 0) as string),
          parse(filtered.get("input_ids", 0) as string),
          parse(filtered.get("message_references", 0) as string),
          parse(filtered.get("metadata", 0) as string),
          parse(filtered.get("scan_events", 0) as string),
          parse(filtered.get("scan_metadata", 0) as string),
          parse(filtered.get("scan_model_usage", 0) as string),
          parse(filtered.get("scan_tags", 0) as string),
          parse(filtered.get("scanner_params", 0) as string),
          parse(filtered.get("transcript_metadata", 0) as string),
          parse(filtered.get("validation_result", 0) as string),
          parse(filtered.get("validation_target", 0) as string),
          simpleValue(filtered.get("value", 0), valueType),
          transcript_agent_args_raw
            ? parse(transcript_agent_args_raw)
            : Promise.resolve(undefined),
          transcript_score_raw
            ? parse(transcript_score_raw)
            : Promise.resolve(undefined),
        ]);

        if (cancelled) {
          return;
        }

        const uuid = filtered.get("uuid", 0) as string | undefined;
        const timestamp = getOptionalDateColumn(filtered, "timestamp");
        const answer = filtered.get("answer", 0) as string | undefined;
        const label = getOptionalColumn<string>(filtered, "label");
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
        const scanErrorRefusal =
          getOptionalColumn<boolean>(filtered, "scan_error_refusal") ?? false;
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

        const transcriptTaskSet = getOptionalColumn<string>(
          filtered,
          "transcript_task_set"
        );

        const transcriptTaskId = getOptionalColumn<string | number>(
          filtered,
          "transcript_task_id"
        );

        const transcriptTaskRepeat = getOptionalColumn<number>(
          filtered,
          "transcript_task_repeat"
        );

        const transcriptDate = getOptionalDateColumn(
          filtered,
          "transcript_date"
        );

        const transcriptAgent = getOptionalColumn<string>(
          filtered,
          "transcript_agent"
        );
        const transcriptModel = getOptionalColumn<string>(
          filtered,
          "transcript_model"
        );
        const transcriptSuccess = getOptionalColumn<boolean>(
          filtered,
          "transcript_success"
        );
        const transcriptTotalTime = getOptionalColumn<number>(
          filtered,
          "transcript_total_time"
        );
        const transcroptTotalTokens = getOptionalColumn<number>(
          filtered,
          "transcropt_total_tokens"
        );
        const transcriptError = getOptionalColumn<string>(
          filtered,
          "transcript_error"
        );
        const transcriptLimit = getOptionalColumn<string>(
          filtered,
          "transcript_limit"
        );

        const baseData = {
          uuid,
          timestamp,
          answer,
          label,
          eventReferences: eventReferences as ScanResultReference[],
          explanation,
          inputIds: inputIds as string[],
          messageReferences: messageReferences as ScanResultReference[],
          metadata: metadata as Record<string, JsonValue>,
          scanError,
          scanErrorTraceback,
          scanErrorRefusal,
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
          transcriptTaskSet,
          transcriptTaskId,
          transcriptTaskRepeat,
          transcriptAgent,
          transcriptAgentArgs: transcriptAgentArgs as Record<string, unknown>,
          transcriptDate,
          transcriptModel,
          transcriptScore,
          transcriptSuccess,
          transcriptTotalTime,
          transcroptTotalTokens,
          transcriptError,
          transcriptLimit,
          validationResult: validationResult as
            | boolean
            | Record<string, boolean>,
          validationTarget: validationTarget as
            | boolean
            | Record<string, boolean>,
          value: value ?? null,
          valueType,
        };

        // Create typed data based on inputType
        let typedData: ScanResultData;
        switch (inputType) {
          case "transcript":
            typedData = {
              ...baseData,
              inputType: "transcript",
            };
            break;
          case "message":
            typedData = {
              ...baseData,
              inputType: "message",
            };
            break;
          case "messages":
            typedData = {
              ...baseData,
              inputType: "messages",
            };
            break;
          case "event":
            typedData = {
              ...baseData,
              inputType: "event",
            };
            break;
          case "events":
            typedData = {
              ...baseData,
              inputType: "events",
            };
            break;
        }

        setScanResultData(typedData);
        setIsLoading(false);
      } catch (error) {
        if (!cancelled) {
          console.error("Error parsing scanner data:", error);
          setScanResultData(undefined);
          setIsLoading(false);
        }
      }
    };

    void parseData();

    return () => {
      cancelled = true;
    };
  }, [filtered]);

  return { data: scanResultData, isLoading };
};

function getOptionalColumn<T>(
  table: ColumnTable,
  columnName: string,
  rowIndex: number = 0
): T | undefined {
  return table.columnNames().includes(columnName)
    ? (table.get(columnName, rowIndex) as T)
    : undefined;
}

function getOptionalDateColumn(
  table: ColumnTable,
  columnName: string,
  rowIndex: number = 0
): Date | undefined {
  const value = getOptionalColumn<string>(table, columnName, rowIndex);
  return value ? new Date(value) : undefined;
}
