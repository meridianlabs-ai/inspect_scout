import { ColumnTable, from } from "arquero";
import JSON5 from "json5";

import { asyncJsonParse } from "../../utils/json-worker";
import { ScannerReference, ValueType } from "../types";

interface Result {
  uuid?: string | null;
  label?: string | null;
  value: unknown;
  type?: ValueType | null;
  answer?: string | null;
  explanation?: string | null;
  metadata?: Record<string, unknown> | null;
  references?: ScannerReference[];
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
  // Check if we have any resultset rows
  const colNames = columnTable.columnNames();
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

        // Override values
        expandedRow.uuid = result.uuid ?? null;
        expandedRow.label = result.label ?? null;
        expandedRow.answer = result.answer ?? null;
        expandedRow.explanation = result.explanation ?? null;

        // Extract validations, if present
        if (row.validation_result && result.label) {
          if (typeof row.validation_result === "string") {
            const parsedValidation = await asyncJsonParse<
              Record<string, boolean>
            >(row.validation_result);

            const resultValidation = parsedValidation[result.label];
            expandedRow.validation_result = resultValidation;
          } else {
            // TODO: how is a non-string value here?
          }
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

  // Combine with non-resultset rows
  if (explodedResultsetRows.length === 0) {
    return otherRows;
  } else {
    // Create an array merging all the rows and convert back to a column table
    const otherRowsArray = otherRows.objects() as Record<string, unknown>[];
    const allRowsArray = [...otherRowsArray, ...explodedResultsetRows];

    // Create new table from combined array
    return from(allRowsArray);
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
