import { Status } from "../../types/api-types";
import { toRelativePath } from "../../utils/path";

/**
 * Gets the display name for a scan.
 *
 * Uses the relative path from the scans directory when available,
 * providing a more informative title that includes the directory structure.
 *
 * @param scan - The scan status object, or undefined if loading
 * @param scansDir - The base scans directory for computing relative paths
 * @returns The scan display name, or undefined if scan is undefined
 */
export function getScanDisplayName(
  scan: Status | undefined,
  scansDir: string | undefined
): string | undefined {
  if (!scan) return undefined;

  // Use relative path if we have a scans directory
  if (scansDir && scan.location) {
    const relativePath = toRelativePath(scan.location, scansDir);
    if (relativePath) {
      return relativePath;
    }
  }

  // Fall back to scan name
  return scan.spec.scan_name === "job" ? "scan" : scan.spec.scan_name;
}
