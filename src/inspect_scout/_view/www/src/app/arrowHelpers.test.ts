import { from } from "arquero";
import { describe, expect, it } from "vitest";

import { parseScanResultData, parseScanResultSummaries } from "./arrowHelpers";
import { ScanResultData, ScanResultSummary } from "./types";

// Typical row data as it would come from arquero .objects()
const typicalSummaryRow = {
  uuid: "test-uuid-123",
  label: "test-label",
  explanation: "Test explanation",
  input_type: "transcript",
  value_type: "object",
  value: '{"score": 0.95}',
  validation_result: "true",
  validation_target: "true",
  event_references: '[{"type":"event","id":"evt-1"}]',
  message_references: "[]",
  transcript_metadata:
    '{"model":"gpt-4","task_name":"test-task","id":"task-1","epoch":1}',
  transcript_source_id: "source-123",
  transcript_task_set: undefined,
  transcript_task_id: undefined,
  transcript_task_repeat: undefined,
  transcript_model: undefined,
  scan_error: undefined,
  scan_error_refusal: false,
  timestamp: "2024-01-15T10:30:00Z",
};

const expectedSummary: Partial<ScanResultSummary> = {
  uuid: "test-uuid-123",
  label: "test-label",
  explanation: "Test explanation",
  inputType: "transcript",
  valueType: "object",
  value: { score: 0.95 },
  validationResult: true,
  validationTarget: true,
  eventReferences: [{ type: "event", id: "evt-1" }],
  messageReferences: [],
  transcriptSourceId: "source-123",
  // These should be resolved from metadata since they're undefined in row
  transcriptModel: "gpt-4",
  transcriptTaskSet: "test-task",
  transcriptTaskId: "task-1",
  transcriptTaskRepeat: 1,
  scanErrorRefusal: false,
};

// Typical column data as it would come from a ColumnTable
const typicalColumnData: Record<string, unknown> = {
  uuid: "data-uuid-456",
  input_type: "message",
  value_type: "number",
  value: 42,
  answer: "test answer",
  validation_result: '{"passed":true}',
  validation_target: '{"passed":true}',
  event_references: "[]",
  message_references: '[{"type":"message","id":"msg-1"}]',
  input_ids: '["id-1","id-2"]',
  metadata: '{"key":"value"}',
  scan_events: "[]",
  scan_metadata: "{}",
  scan_model_usage: "{}",
  scan_tags: '["tag1"]',
  scanner_params: "{}",
  transcript_metadata: '{"model":"claude-3"}',
  transcript_source_id: "src-456",
  transcript_source_uri: "s3://bucket/path",
  transcript_id: "trans-123",
  scan_id: "scan-789",
  scan_total_tokens: 1500,
  scanner_file: "scanner.py",
  scanner_key: "test_scanner",
  scanner_name: "Test Scanner",
  explanation: "Data explanation",
  scan_error: null,
  scan_error_traceback: null,
  scan_error_refusal: false,
  timestamp: "2024-02-20T14:00:00Z",
};

const expectedData: Partial<ScanResultData> = {
  uuid: "data-uuid-456",
  inputType: "message",
  valueType: "number",
  value: 42,
  validationResult: { passed: true },
  validationTarget: { passed: true },
  eventReferences: [],
  messageReferences: [{ type: "message", id: "msg-1" }],
  inputIds: ["id-1", "id-2"],
  metadata: { key: "value" },
  scanEvents: [],
  scanMetadata: {},
  scanModelUsage: {},
  scanTags: ["tag1"],
  scannerParams: {},
  transcriptSourceId: "src-456",
  transcriptSourceUri: "s3://bucket/path",
  transcriptId: "trans-123",
  scanId: "scan-789",
  scanTotalTokens: 1500,
  scannerFile: "scanner.py",
  scannerKey: "test_scanner",
  scannerName: "Test Scanner",
  explanation: "Data explanation",
  scanErrorRefusal: false,
  transcriptModel: "claude-3",
};

describe("parseScanResultSummaries", () => {
  it.each<[object[], Partial<ScanResultSummary>[], string]>([
    [[], [], "empty array"],
    [[typicalSummaryRow], [expectedSummary], "typical row"],
  ])(
    "returns expected output for %s",
    async (input, expected, _desc: string) => {
      const result = await parseScanResultSummaries(input);
      expect(result).toHaveLength(expected.length);
      for (const [i, r] of result.entries()) {
        expect(r).toMatchObject(expected[i]!);
      }
    }
  );
});

describe("parseScanResultData", () => {
  it.each<[Record<string, unknown>, Partial<ScanResultData>, string]>([
    [typicalColumnData, expectedData, "typical data"],
  ])(
    "returns expected output for %s",
    async (input, expected, _desc: string) => {
      const table = from([input]);
      const result = await parseScanResultData(table);
      expect(result).toMatchObject(expected);
    }
  );
});
