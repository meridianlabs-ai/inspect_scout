import type {
  ActiveScansResponse,
  AppConfig,
  MessagesEventsResponse,
  ProjectConfig,
  ScanRow,
  ScansResponse,
  Status,
  TranscriptInfo,
  TranscriptsResponse,
} from "../../src/types/api-types";

export function createAppConfig(
  overrides?: Partial<AppConfig>,
): AppConfig {
  return {
    home_dir: "/home/test",
    project_dir: "/home/test/project",
    filter: [],
    scans: { dir: "/home/test/project/.scans", source: "project" },
    transcripts: {
      dir: "/home/test/project/.transcripts",
      source: "project",
    },
    ...overrides,
  } satisfies AppConfig;
}

export function createTranscriptInfo(
  overrides: Partial<TranscriptInfo> & { transcript_id: string },
): TranscriptInfo {
  return {
    metadata: {},
    ...overrides,
  };
}

export function createScanRow(
  overrides: Partial<ScanRow> & { scan_id: string },
): ScanRow {
  return {
    location: `/scans/${overrides.scan_id}`,
    packages: {},
    scan_name: overrides.scan_id,
    scanners: "",
    status: "complete",
    tags: "",
    timestamp: "2024-01-01T00:00:00Z",
    total_errors: 0,
    total_results: 0,
    total_tokens: 0,
    transcript_count: 0,
    ...overrides,
  };
}

export function createTranscriptsResponse(
  items: TranscriptInfo[] = [],
): TranscriptsResponse {
  return {
    items,
    next_cursor: null,
    total_count: items.length,
  } satisfies TranscriptsResponse;
}

export function createScansResponse(
  items: ScanRow[] = [],
): ScansResponse {
  return {
    items,
    next_cursor: null,
    total_count: items.length,
  } satisfies ScansResponse;
}

export function createActiveScansResponse(): ActiveScansResponse {
  return {
    items: {},
  } satisfies ActiveScansResponse;
}

export function createProjectConfig(): ProjectConfig {
  return {
    filter: [],
  } satisfies ProjectConfig;
}

export function createStatus(overrides?: Partial<Status>): Status {
  return {
    complete: true,
    errors: [],
    location:
      "/home/test/project/.scans/scan_id=aBcDeFgHiJkLmNoPqRsTuV",
    spec: {
      scan_id: "aBcDeFgHiJkLmNoPqRsTuV",
      scan_name: "eval-safety",
      options: { max_transcripts: 25 },
      packages: {},
      scanners: {},
      timestamp: "2024-01-01T00:00:00Z",
    },
    summary: { complete: true, scanners: {} },
    ...overrides,
  } satisfies Status;
}

export function createMessagesEventsResponse(
  overrides?: Partial<MessagesEventsResponse>,
): MessagesEventsResponse {
  return {
    messages: [],
    events: [],
    ...overrides,
  } satisfies MessagesEventsResponse;
}
