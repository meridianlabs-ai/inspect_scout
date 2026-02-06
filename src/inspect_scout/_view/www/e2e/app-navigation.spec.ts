import { test, expect } from "./fixtures/app";

test("activity bar renders with expected items", async ({ page }) => {
  await page.goto("/");

  await expect(page.locator("#project")).toBeVisible();
  await expect(page.locator("#transcripts")).toBeVisible();
  await expect(page.locator("#scans")).toBeVisible();
  await expect(page.locator("#validation")).toBeVisible();
});

test("default route is /transcripts when transcripts dir exists", async ({
  page,
}) => {
  await page.goto("/");

  // Wait for the redirect to complete
  await expect(page).toHaveURL(/#\/transcripts/);
});

test("clicking activity bar items navigates to correct routes", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page).toHaveURL(/#\/transcripts/);

  await page.locator("#project").click();
  await expect(page).toHaveURL(/#\/project/);

  await page.locator("#scans").click();
  await expect(page).toHaveURL(/#\/scans/);

  await page.locator("#validation").click();
  await expect(page).toHaveURL(/#\/validation/);

  await page.locator("#transcripts").click();
  await expect(page).toHaveURL(/#\/transcripts/);
});
