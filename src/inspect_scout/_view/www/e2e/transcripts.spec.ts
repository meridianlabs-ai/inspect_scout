import { http, HttpResponse } from "msw";

import { test, expect } from "./fixtures/app";
import {
  createTranscriptInfo,
  createTranscriptsResponse,
} from "./fixtures/test-data";

test.describe("Transcripts page", () => {
  test("renders transcript grid with data", async ({ page, network }) => {
    network.use(
      http.post("*/api/v2/transcripts/:dir", () =>
        HttpResponse.json(
          createTranscriptsResponse([
            createTranscriptInfo({
              transcript_id: "t-001",
              task_id: "my-task",
              model: "claude-3",
              success: true,
            }),
            createTranscriptInfo({
              transcript_id: "t-002",
              task_id: "other-task",
              model: "gpt-4",
              success: false,
            }),
          ]),
        ),
      ),
    );

    await page.goto("/#/transcripts");

    // Grid renders with transcript data
    await expect(page.getByText("my-task").first()).toBeVisible();
    await expect(page.getByText("other-task").first()).toBeVisible();

    // Footer shows item count
    await expect(page.locator("#transcripts-footer")).toContainText("2 items");
  });

  test("shows empty state when no transcripts exist", async ({ page }) => {
    await page.goto("/#/transcripts");

    // Footer shows 0 items
    await expect(page.locator("#transcripts-footer")).toContainText("0 items");
  });
});
