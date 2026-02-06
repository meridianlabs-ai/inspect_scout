import { http, HttpResponse } from "msw";

import { test, expect } from "./fixtures/app";

test.describe("Error handling", () => {
  test("transcripts page shows error panel on API failure", async ({
    page,
    network,
  }) => {
    network.use(
      http.post("*/api/v2/transcripts/:dir", () =>
        HttpResponse.text("Internal Server Error", { status: 500 }),
      ),
    );

    await page.goto("/#/transcripts");

    // React Query retries 3x with exponential backoff before surfacing the error
    await expect(page.getByText("Error Loading Transcript")).toBeVisible({
      timeout: 15_000,
    });
  });

  test("scans page shows error panel on API failure", async ({
    page,
    network,
  }) => {
    network.use(
      http.post("*/api/v2/scans/:dir", () =>
        HttpResponse.text("Internal Server Error", { status: 500 }),
      ),
    );

    await page.goto("/#/scans");

    // React Query retries 3x with exponential backoff before surfacing the error
    await expect(page.getByText("Error Loading Scans")).toBeVisible({
      timeout: 15_000,
    });
  });
});
