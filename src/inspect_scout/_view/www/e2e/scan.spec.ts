import { http, HttpResponse } from "msw";

import { encodeBase64Url } from "../src/utils/base64url";

import { test, expect } from "./fixtures/app";
import {
  createScanRow,
  createScansResponse,
  createStatus,
} from "./fixtures/test-data";

const SCANS_DIR = "/home/test/project/.scans";
const SCAN_ID = "aBcDeFgHiJkLmNoPqRsTuV";
const SCAN_LOCATION = `${SCANS_DIR}/scan_id=${SCAN_ID}`;
const SCAN_RELATIVE_PATH = `scan_id=${SCAN_ID}`;

test("clicking a scan row opens the scan detail panel", async ({
  page,
  network,
}) => {
  network.use(
    http.post("*/api/v2/scans/:dir", () =>
      HttpResponse.json(
        createScansResponse([
          createScanRow({
            scan_id: SCAN_ID,
            scan_name: "eval-safety",
            location: SCAN_LOCATION,
          }),
        ]),
      ),
    ),
    http.get("*/api/v2/scans/:dir/:scanPath", () =>
      HttpResponse.json(
        createStatus({
          location: SCAN_LOCATION,
          spec: {
            scan_id: SCAN_ID,
            scan_name: "eval-safety",
            options: { max_transcripts: 25 },
            packages: {},
            scanners: {},
            timestamp: "2024-01-15T10:30:00Z",
          },
        }),
      ),
    ),
  );

  await page.goto("/#/scans");
  await page.getByText("eval-safety").first().click();

  await expect(page.locator("h1")).toContainText("eval-safety");
  await expect(page.getByText("Complete")).toBeVisible();
});

test("scan panel shows error state when scan API fails", async ({
  page,
  network,
}) => {
  network.use(
    http.get("*/api/v2/scans/:dir/:scanPath", () =>
      HttpResponse.text("Internal Server Error", { status: 500 }),
    ),
  );

  const encodedDir = encodeBase64Url(SCANS_DIR);
  await page.goto(`/#/scan/${encodedDir}/${SCAN_RELATIVE_PATH}`);

  await expect(page.getByText("Error Loading Scan")).toBeVisible({
    timeout: 15_000,
  });
});
