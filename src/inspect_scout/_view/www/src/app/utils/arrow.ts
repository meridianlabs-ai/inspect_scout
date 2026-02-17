import { ColumnTable, from } from "arquero";
import JSON5 from "json5";

import { asyncJsonParse } from "../../utils/json-worker";
import { ScanResultReference, ValueType } from "../types";

interface Result {
  uuid?: string | null;
  label?: string | null;
  value: unknown;
  type?: ValueType | null;
  answer?: string | null;
  explanation?: string | null;
  metadata?: Record<string, unknown> | null;
  references?: ScanResultReference[];
}

// Expand rows where value_type == "resultset" into multiple rows.
//
// For rows with value_type == "resultset", the value field contains a JSON-encoded
// list of Result objects. This function:
// 1. Parses the JSON value into a list
// 2. Explodes each list element into its own row using Arquero's unroll()
// 3. Normalizes the Result fields into columns (uuid, label, value, etc.)
// 4. Applies type casting to the expanded value column
//
// I tested an alternative approach to this using Arquero's unroll() function
// directly in a derive() expression, but it wasn't faster (was actually a
// touch slower anecdotally) and was a much more complex set of operations.
// I omit that function and instead just operate on the rows directly.
export async function expandResultsetRows(
  columnTable: ColumnTable
): Promise<ColumnTable> {
  // Ensure that each row in the table has an "identifier" column (this is used as a unique key for
  // referencing rows since code below may expand one row with a resultset into multiple rows.
  // We use the existing "uuid" column if it exists, otherwise we generate a random UUID. It is expected that the resultset expansion
  // will overwrite this value for expanded rows
  const colNames = columnTable.columnNames();
  if (!colNames.includes("identifier")) {
    const numRows = columnTable.numRows();
    const identifiers = new Array<string>(numRows);
    if (colNames.includes("uuid")) {
      const uuids = columnTable.array("uuid") as (string | null | undefined)[];
      for (let i = 0; i < numRows; i++) {
        identifiers[i] = uuids[i] ?? crypto.randomUUID();
      }
    } else {
      for (let i = 0; i < numRows; i++) {
        identifiers[i] = crypto.randomUUID();
      }
    }
    columnTable = columnTable.assign({ identifier: identifiers });
  }

  // Check if we have any resultset rows
  if (
    !colNames.includes("value_type") ||
    !colNames.includes("value") ||
    columnTable.numRows() === 0
  ) {
    return columnTable;
  }

  // Are there any results sets to explode?
  const resultsetCount = columnTable
    .filter((d: { value_type: string }) => d.value_type === "resultset")
    .numRows();
  if (resultsetCount === 0) {
    // No result sets
    return columnTable;
  }

  // Split into resultset and non-resultset rows
  const resultsetRows = columnTable.filter(
    (d: { value_type: string }) => d.value_type === "resultset"
  );
  const otherRows = columnTable.filter(
    (d: { value_type: string }) => d.value_type !== "resultset"
  );

  // Parse JSON value strings and expand into multiple rows
  // (Arquero doesn't support try-catch in derive expressions, so we do this in plain JS)
  const resultObjs = resultsetRows.objects() as Record<string, unknown>[];
  const explodedResultsetRows: Record<string, unknown>[] = [];

  for (const row of resultObjs) {
    try {
      // Get the result set value
      const valueStr = row.value as string;
      const results = valueStr ? JSON5.parse<Result[]>(valueStr) : [];

      // If the row has an empty result set, just leave it
      // intact
      if (!results || results.length === 0) {
        const expandedRow = { ...row };
        expandedRow.value = null;
        expandedRow.value_type = "null";
        explodedResultsetRows.push(expandedRow);
        continue;
      }

      for (const result of results) {
        const expandedRow = { ...row };

        // Record the source identifier
        expandedRow.identifier = result.uuid ?? crypto.randomUUID();

        // Override values

        expandedRow.label = result.label ?? null;
        expandedRow.answer = result.answer ?? null;
        expandedRow.explanation = result.explanation ?? null;

        // Extract label-based validation, if present
        if (
          row.validation_result &&
          typeof row.validation_result === "string"
        ) {
          expandedRow.validation_result = await extractLabelValidation(
            expandedRow,
            row.validation_result
          );
        }

        // Handle metadata
        const metadata = result.metadata ?? {};
        expandedRow.metadata = maybeSerializeValue(metadata);

        // Determine value_type
        const valueType = result.type ?? inferType(result.value);
        expandedRow.value_type = valueType;

        // Cast the value based on its type
        const value = maybeSerializeValue(result.value);
        expandedRow.value = value;

        // Split into message_references and event_references
        const references = result.references ?? [];
        const messageRefs = references.filter((ref) => ref.type === "message");
        const eventRefs = references.filter((ref) => ref.type === "event");
        expandedRow.message_references = maybeSerializeValue(messageRefs);
        expandedRow.event_references = maybeSerializeValue(eventRefs);

        // don't clear out scan execution fields to avoid incorrect aggregation
        // (these represent the scan execution, not individual results)
        // (since these aren't for computation, we're keeping them for display)
        // expandedRow.scan_total_tokens = null;
        // expandedRow.scan_model_usage = null;

        explodedResultsetRows.push(expandedRow);
      }
    } catch (error) {
      console.error("Failed to parse resultset value:", error);
      continue;
    }
  }

  // Create synthetic rows for missing labels with negative expected values
  const syntheticRows = await createSyntheticRows(
    explodedResultsetRows,
    resultObjs
  );

  // Combine with non-resultset rows
  if (explodedResultsetRows.length === 0) {
    return otherRows;
  } else {
    // Create an array merging all the rows and convert back to a column table
    const otherRowsArray = otherRows.objects() as Record<string, unknown>[];

    const allRowsArray = [
      ...otherRowsArray,
      ...explodedResultsetRows,
      ...syntheticRows,
    ];

    // Create new table from combined array
    return from(allRowsArray);
  }
}

async function extractLabelValidation(
  row: Record<string, unknown>,
  validationResultStr: string
): Promise<boolean | string | null | unknown> {
  if (!row.label || typeof row.label !== "string") {
    return validationResultStr;
  }

  try {
    const parsedValidation = await asyncJsonParse<unknown>(validationResultStr);

    // Check if this is label-based validation (dict of label -> bool)
    if (
      typeof parsedValidation === "object" &&
      parsedValidation !== null &&
      !Array.isArray(parsedValidation)
    ) {
      // Extract the validation result for this specific label
      const validationDict = parsedValidation as Record<string, boolean>;
      const labelValidation = validationDict[row.label];
      return labelValidation ?? null;
    }

    // Not label-based, return as-is
    return parsedValidation;
  } catch (error) {
    // If parsing fails, return original string
    return validationResultStr;
  }
}

/**
 * Create synthetic rows for missing labels with negative expected values.
 *
 * When validation_target contains expected labels that are not present in the
 * expanded results, and the expected value is "negative" (false, null, etc.),
 * this creates synthetic rows for those missing labels.
 *
 * @param expandedRows - The expanded result rows
 * @param resultsetRows - The original resultset rows (used as template)
 * @returns Array of synthetic rows to add
 */
async function createSyntheticRows(
  expandedRows: Record<string, unknown>[],
  resultsetRows: Record<string, unknown>[]
): Promise<Record<string, unknown>[]> {
  if (resultsetRows.length === 0 || expandedRows.length === 0) {
    return [];
  }

  // Check if we have validation_target in the first row
  const firstRow = expandedRows[0];
  if (
    !firstRow ||
    !firstRow.validation_target ||
    typeof firstRow.validation_target !== "string"
  ) {
    return [];
  }

  try {
    // Parse validation_target to check if it's label-based (a dict)
    const parsedTarget = await asyncJsonParse<unknown>(
      firstRow.validation_target
    );
    if (
      typeof parsedTarget !== "object" ||
      parsedTarget === null ||
      Array.isArray(parsedTarget)
    ) {
      return [];
    }

    const validationTarget = parsedTarget as Record<string, unknown>;

    // Parse validation_result
    const parsedResult = firstRow.validation_result
      ? await asyncJsonParse<unknown>(
          typeof firstRow.validation_result === "string"
            ? firstRow.validation_result
            : JSON.stringify(firstRow.validation_result)
        )
      : {};
    const validationResults =
      typeof parsedResult === "object" && !Array.isArray(parsedResult)
        ? (parsedResult as Record<string, unknown>)
        : {};

    // Get all labels present in expanded rows
    const presentLabels = new Set(
      expandedRows
        .map((row) => row.label)
        .filter((label) => label !== null && label !== undefined)
    );

    // Get expected labels from validation_target
    const expectedLabels = Object.keys(validationTarget);

    // Missing labels = expected but not present
    const missingLabels = expectedLabels.filter(
      (label) => !presentLabels.has(label)
    );

    // Create synthetic rows for missing labels with negative expected values
    const syntheticRows: Record<string, unknown>[] = [];
    const negativeValues = [false, null, "NONE", "none", 0, ""];

    for (const label of missingLabels) {
      const expectedValue = validationTarget[label];

      // Only create synthetic row if expected value is negative
      if (!negativeValues.includes(expectedValue as never)) {
        continue;
      }

      // Get a template row from the first resultset row
      const templateRow = { ...resultsetRows[0] };

      // Set result-specific fields for the synthetic row
      templateRow.label = label;
      templateRow.value = expectedValue;
      templateRow.value_type =
        typeof expectedValue === "boolean" ? "boolean" : "null";
      templateRow.answer = null;
      templateRow.explanation = null;
      templateRow.metadata = maybeSerializeValue({});
      templateRow.message_references = maybeSerializeValue([]);
      templateRow.event_references = maybeSerializeValue([]);
      templateRow.uuid = null;

      // Set validation result for this synthetic row
      templateRow.validation_result = validationResults[label] ?? null;

      // NULL out error fields
      templateRow.scan_error = null;
      templateRow.scan_error_traceback = null;
      templateRow.scan_error_type = null;

      // NULL out scan execution fields
      templateRow.scan_total_tokens = null;
      templateRow.scan_model_usage = null;

      syntheticRows.push(templateRow);
    }

    return syntheticRows;
  } catch (error) {
    // If parsing fails, no synthetic rows
    return [];
  }
}

function inferType(value: unknown): ValueType {
  if (typeof value === "boolean") {
    return "boolean";
  } else if (typeof value === "number") {
    return "number";
  } else if (typeof value === "string") {
    return "string";
  } else if (Array.isArray(value)) {
    return "array";
  } else if (value !== null && typeof value === "object") {
    return "object";
  }
  return "null";
}

const maybeSerializeValue = (
  value: unknown
): string | number | boolean | null => {
  if (value === undefined || value === null) {
    return null;
  }
  if (
    typeof value === "string" ||
    typeof value === "number" ||
    typeof value === "boolean"
  ) {
    return value;
  }
  // Convert complex types (arrays, objects) to JSON strings
  return JSON5.stringify(value);
};
