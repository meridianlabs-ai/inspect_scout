import { useEffect } from "react";

const APP_NAME = "Inspect Scout";

/**
 * Sets the document title based on provided segments.
 *
 * Title segments are joined with " - " and the app name is appended.
 * Falsy values (undefined, null, empty string) are filtered out automatically,
 * making it easy to handle loading states.
 *
 * @param segments - Array of title segments, from most specific to least specific.
 *                   Falsy values are filtered out.
 *
 * @example
 * ```tsx
 * // Top-level activity: "Scans - Inspect Scout"
 * useDocumentTitle("Scans");
 *
 * // Detail view: "my-scan - Scans - Inspect Scout"
 * useDocumentTitle(scanName, "Scans");
 *
 * // Nested detail: "task-123 - my-scan - Scans - Inspect Scout"
 * useDocumentTitle(taskName, scanName, "Scans");
 *
 * // Loading state: undefined is filtered out → "Scans - Inspect Scout"
 * useDocumentTitle(loadingScanName, "Scans"); // loadingScanName is undefined
 * ```
 */
export function useDocumentTitle(
  ...segments: Array<string | undefined | null>
): void {
  useEffect(() => {
    // Filter out falsy values and build title
    const filtered = segments.filter((s): s is string => Boolean(s));
    const title =
      filtered.length > 0 ? `${filtered.join(" - ")} - ${APP_NAME}` : APP_NAME;

    document.title = title;
    // No cleanup: let the next component set its own title to avoid flicker
  }, [...segments]);
}
