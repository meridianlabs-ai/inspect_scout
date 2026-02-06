import type {
  ActiveScansResponse,
  AppConfig,
  ProjectConfig,
  ScansResponse,
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

export function createTranscriptsResponse(): TranscriptsResponse {
  return {
    items: [],
    next_cursor: null,
    total_count: 0,
  } satisfies TranscriptsResponse;
}

export function createScansResponse(): ScansResponse {
  return {
    items: [],
    next_cursor: null,
    total_count: 0,
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
