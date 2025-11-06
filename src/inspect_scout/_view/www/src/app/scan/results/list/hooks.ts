import { ColumnTable } from "arquero";
import { useMemo } from "react";

import { EventType } from "../../../../transcript/types";
import { ModelUsage, Transcript } from "../../../../types";
import { Events, JsonValue } from "../../../../types/log";

import {
  MessageType,
  ScannerData,
  ScannerPreview,
  ScannerReference,
} from "./types";

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

export const useScannerData = (row: number, columnTable: ColumnTable) => {
  const scannerSummaries = useMemo(() => {
    const rowData = columnTable.objects();
    const r = rowData[row] as Record<string, unknown>;
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
