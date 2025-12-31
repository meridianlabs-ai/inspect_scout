/**
 * Utilities for working with dates and native HTML5 date/datetime inputs.
 */

/**
 * Formats a date value for use with native HTML5 date input (type="date").
 * Returns format: YYYY-MM-DD
 *
 * @param value - The date value (Date, ISO string, or timestamp)
 * @returns Formatted date string in YYYY-MM-DD format, or empty string if invalid
 */
export function formatDateForInput(
  value: Date | string | number | null | undefined
): string {
  if (value === null || value === undefined) {
    return "";
  }

  const date = new Date(value);
  if (isNaN(date.getTime())) {
    return "";
  }

  // Format as YYYY-MM-DD for date input
  const dateOnly = date.toISOString().split("T")[0];
  return dateOnly ?? "";
}

/**
 * Formats a datetime value for use with native HTML5 datetime-local input (type="datetime-local").
 * Returns format: YYYY-MM-DDTHH:mm
 *
 * @param value - The datetime value (Date, ISO string, or timestamp)
 * @returns Formatted datetime string in YYYY-MM-DDTHH:mm format, or empty string if invalid
 */
export function formatDateTimeForInput(
  value: Date | string | number | null | undefined
): string {
  if (value === null || value === undefined) {
    return "";
  }

  const date = new Date(value);
  if (isNaN(date.getTime())) {
    return "";
  }

  // Format as YYYY-MM-DDTHH:mm for datetime-local input
  const isoStr = date.toISOString();
  return isoStr.substring(0, 16); // YYYY-MM-DDTHH:mm
}

/**
 * Parses a date or datetime string from native HTML5 inputs and returns an ISO string.
 * Handles both date (YYYY-MM-DD) and datetime-local (YYYY-MM-DDTHH:mm) formats.
 *
 * @param value - The date/datetime string from the native input
 * @returns ISO 8601 datetime string, or undefined if invalid
 */
export function parseDateFromInput(
  value: string
): string | undefined {
  if (!value || value.trim() === "") {
    return undefined;
  }

  const date = new Date(value);
  if (isNaN(date.getTime())) {
    return undefined;
  }

  // Return the ISO string for backend filtering
  return date.toISOString();
}

/**
 * Checks if a value is a valid date.
 *
 * @param value - The value to check
 * @returns true if the value is a valid date
 */
export function isValidDate(
  value: Date | string | number | null | undefined
): boolean {
  if (value === null || value === undefined) {
    return false;
  }

  const date = new Date(value);
  return !isNaN(date.getTime());
}
