import { http, HttpResponse } from "msw";

import type {
  MessagesEventsResponse,
  TranscriptInfo,
  TranscriptsResponse,
} from "../src/types/api-types";
import { encodeBase64Url } from "../src/utils/base64url";

import { test, expect } from "./fixtures/app";
import {
  createMessagesEventsResponse,
  createTranscriptInfo,
  createTranscriptsResponse,
} from "./fixtures/test-data";

const TRANSCRIPTS_DIR = "/home/test/project/.transcripts";
const TRANSCRIPT_ID = "t-001";

test("clicking a transcript row opens the transcript detail panel", async ({
  page,
  network,
}) => {
  network.use(
    http.post("*/api/v2/transcripts/:dir", () =>
      HttpResponse.json<TranscriptsResponse>(
        createTranscriptsResponse([
          createTranscriptInfo({
            transcript_id: TRANSCRIPT_ID,
            task_id: "my-task",
            model: "claude-3",
            date: "2024-01-15T10:30:00Z",
          }),
        ]),
      ),
    ),
    http.get("*/api/v2/transcripts/:dir/:id/info", () =>
      HttpResponse.json<TranscriptInfo>(
        createTranscriptInfo({
          transcript_id: TRANSCRIPT_ID,
          task_id: "my-task",
          model: "claude-3",
          date: "2024-01-15T10:30:00Z",
        }),
      ),
    ),
    http.get("*/api/v2/transcripts/:dir/:id/messages-events", () =>
      HttpResponse.json<MessagesEventsResponse>(createMessagesEventsResponse()),
    ),
  );

  await page.goto("/#/transcripts");
  await page.getByText("my-task").first().click();

  await expect(page.getByText("my-task").first()).toBeVisible();
  await expect(page.getByText("claude-3")).toBeVisible();
});

test("transcript panel shows error state when API fails", async ({
  page,
  network,
  disableRetries: _,
}) => {
  network.use(
    http.get("*/api/v2/transcripts/:dir/:id/info", () =>
      HttpResponse.text("Internal Server Error", { status: 500 }),
    ),
  );

  const encodedDir = encodeBase64Url(TRANSCRIPTS_DIR);
  await page.goto(
    `/#/transcripts/${encodedDir}/${TRANSCRIPT_ID}`,
  );

  await expect(page.getByText("Error Loading Transcript")).toBeVisible();
});
