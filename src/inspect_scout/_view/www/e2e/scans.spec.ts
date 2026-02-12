import { http, HttpResponse } from "msw";

import type { ScansResponse } from "../src/types/api-types";

import { test, expect } from "./fixtures/app";
import { createScanRow, createScansResponse } from "./fixtures/test-data";

test("scans page renders grid with data", async ({ page, network }) => {
  network.use(
    http.post("*/api/v2/scans/:dir", () =>
      HttpResponse.json<ScansResponse>(
        createScansResponse([
          createScanRow({
            scan_id: "scan-001",
            scan_name: "eval-safety",
            status: "complete",
            total_results: 42,
          }),
          createScanRow({
            scan_id: "scan-002",
            scan_name: "eval-quality",
            status: "active",
            total_results: 10,
          }),
        ]),
      ),
    ),
  );

  await page.goto("/#/scans");

  // Grid renders with scan data
  await expect(page.getByText("eval-safety").first()).toBeVisible();
  await expect(page.getByText("eval-quality").first()).toBeVisible();

  // Footer shows item count
  await expect(page.locator("#scan-job-footer")).toContainText("2 items");
});

test("scans page shows empty state when no scans exist", async ({ page }) => {
  await page.goto("/#/scans");

  // Footer shows 0 items
  await expect(page.locator("#scan-job-footer")).toContainText("0 items");
});

test("scans page shows error panel on API failure", async ({
  page,
  network,
  disableRetries: _,
}) => {
  network.use(
    http.post("*/api/v2/scans/:dir", () =>
      HttpResponse.text("Internal Server Error", { status: 500 }),
    ),
  );

  await page.goto("/#/scans");

  await expect(page.getByText("Error Loading Scans")).toBeVisible();
});
