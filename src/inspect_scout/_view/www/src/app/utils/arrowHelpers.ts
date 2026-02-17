import { ColumnTable } from "arquero";

import { Event, JsonValue, ModelUsage } from "../../types/api-types";
import { isJson } from "../../utils/json";
import { asyncJsonParse } from "../../utils/json-worker";
import {
  ScanResultData,
  ScanResultReference,
  ScanResultSummary,
} from "../types";

export const parseScanResultData = async (
  filtered: ColumnTable
): Promise<ScanResultData> => {
  const valueType = filtered.get("value_type", 0) as ValueType;

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

  // Note that validation_result and validation_target will always a JSON deserializable string as of Jan 7 2026, but prior to this it could be stored as a boolean directly. This conditionality deals with that.
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
    parseJson(filtered.get("event_references", 0) as string),
    parseJson(filtered.get("input_ids", 0) as string),
    parseJson(filtered.get("message_references", 0) as string),
    parseJson(filtered.get("metadata", 0) as string),
    parseJson(filtered.get("scan_events", 0) as string),
    parseJson(filtered.get("scan_metadata", 0) as string),
    parseJson(filtered.get("scan_model_usage", 0) as string),
    parseJson(filtered.get("scan_tags", 0) as string),
    parseJson(filtered.get("scanner_params", 0) as string),
    parseJson(filtered.get("transcript_metadata", 0) as string),
    tryParseJson<boolean | Record<string, boolean>>(
      filtered.get("validation_result", 0)
    ),
    tryParseJson<JsonValue>(filtered.get("validation_target", 0)),
    parseSimpleValue(filtered.get("value", 0), valueType),
    transcript_agent_args_raw
      ? parseJson(transcript_agent_args_raw)
      : Promise.resolve(undefined),
    transcript_score_raw !== null && transcript_score_raw !== undefined
      ? parseJsonValue(transcript_score_raw)
      : Promise.resolve(undefined),
  ]);

  const identifier = filtered.get("identifier", 0) as string;
  const uuid = filtered.get("uuid", 0) as string | undefined;
  const timestamp = getOptionalColumn<string>(filtered, "timestamp");
  const answer = filtered.get("answer", 0) as string | undefined;
  const label = getOptionalColumn<string>(filtered, "label");
  const explanation = filtered.get("explanation", 0) as string | undefined;
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
  const transcriptSourceId = filtered.get("transcript_source_id", 0) as string;
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
  const transcriptDate = getOptionalColumn<string>(filtered, "transcript_date");
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
  const transcriptTotalTokens = getOptionalColumn<number>(
    filtered,
    "transcript_total_tokens"
  );
  const transcriptMessageCount = getOptionalColumn<number>(
    filtered,
    "transcript_message_count"
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
    identifier,
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
    scanEvents: scanEvents as Event[],
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
    transcriptTotalTokens,
    transcriptMessageCount,
    transcriptError,
    transcriptLimit,
    validationResult,
    validationTarget,
    value: value ?? null,
    valueType,
  };

  // Resolve old values from the metadata if not present directly
  // this should only be hit if the scan was old enough to not have
  // these fields
  resolveTranscriptPropertiesFromMetadata(baseData);

  return { ...baseData, inputType };
};

export const parseScanResultSummaries = async (
  rowData: object[]
): Promise<ScanResultSummary[]> =>
  Promise.all(
    rowData.map(async (row) => {
      const r = row as Record<string, unknown>;

      const valueType = r.value_type as ValueType;

      // Note that validation_result and validation_target will always a JSON deserializable string as of Jan 7 2026, but prior to this it could be stored as a boolean directly. This conditionality deals with that.
      const [
        validationResult,
        validationTarget,
        transcriptMetadata,
        eventReferences,
        messageReferences,
        value,
      ] = await Promise.all([
        tryParseJson<boolean | Record<string, boolean>>(r.validation_result),
        tryParseJson<JsonValue>(r.validation_target),
        parseJson<Record<string, JsonValue>>(r.transcript_metadata as string),
        parseJson(r.event_references as string),
        parseJson(r.message_references as string),
        parseSimpleValue(r.value, valueType),
      ]);

      const baseSummary = {
        identifier: r.identifier as string,
        uuid: r.uuid as string | undefined,
        label: r.label as string | undefined,
        explanation: r.explanation as string,
        eventReferences: eventReferences as ScanResultReference[],
        messageReferences: messageReferences as ScanResultReference[],
        validationResult: validationResult,
        validationTarget: validationTarget,
        value: value ?? null,
        valueType,
        transcriptTaskSet: r.transcript_task_set as string | undefined,
        transcriptTaskId: r.transcript_task_id as string | number | undefined,
        transcriptTaskRepeat: r.transcript_task_repeat as number | undefined,
        transcriptModel: r.transcript_model as string | undefined,
        transcriptMetadata: transcriptMetadata || {},
        transcriptSourceId: r.transcript_source_id as string,
        scanError: r.scan_error as string,
        scanErrorRefusal: r.scan_error_refusal as boolean,
        timestamp: r.timestamp ? (r.timestamp as string) : undefined,
      };

      resolveTranscriptPropertiesFromMetadata(baseSummary);

      const inputType = r.input_type as
        | "transcript"
        | "message"
        | "messages"
        | "event"
        | "events";

      return { ...baseSummary, inputType };
    })
  );

function resolveTranscriptPropertiesFromMetadata<
  T extends {
    transcriptModel?: string;
    transcriptTaskSet?: string;
    transcriptTaskId?: string | number;
    transcriptTaskRepeat?: number;
    transcriptMetadata: Record<string, unknown>;
  },
>(data: T): void {
  if (data.transcriptModel === undefined) {
    data.transcriptModel = data.transcriptMetadata["model"] as string;
  }

  if (data.transcriptTaskSet === undefined) {
    data.transcriptTaskSet = data.transcriptMetadata["task_name"] as string;
  }

  if (data.transcriptTaskId === undefined) {
    data.transcriptTaskId = data.transcriptMetadata["id"] as string | number;
  }

  if (data.transcriptTaskRepeat === undefined) {
    data.transcriptTaskRepeat = data.transcriptMetadata["epoch"] as number;
  }
}

const parseJson = async <T>(text: string | null): Promise<T | undefined> =>
  text !== null ? asyncJsonParse<T>(text) : undefined;

const tryParseJson = async <T>(text: unknown): Promise<T> => {
  try {
    return await asyncJsonParse<T>(text as string);
  } catch {
    return text as T;
  }
};

type ValueType = "string" | "number" | "boolean" | "null" | "array" | "object";

const parseSimpleValue = (
  val: unknown,
  valueType: ValueType
): Promise<
  string | number | boolean | null | unknown[] | object | undefined
> =>
  valueType === "object" || valueType === "array"
    ? parseJson<object | unknown[]>(val as string)
    : Promise.resolve(val as string | number | boolean | null);

const parseJsonValue = (val?: unknown): Promise<JsonValue | undefined> => {
  if (!val) {
    return Promise.resolve(undefined);
  }

  if (typeof val === "string" && isJson(val)) {
    return parseJson<JsonValue>(val).then((parsed) => parsed as JsonValue);
  } else {
    return Promise.resolve(val as JsonValue);
  }
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
