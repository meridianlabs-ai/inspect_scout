import {
  tableFromIPC,
  tableToIPC,
  Codec,
  compressionRegistry,
  CompressionType,
} from "apache-arrow";
import type { ColumnTable } from "arquero";
import { escape, fromArrow } from "arquero";
import * as lz4js from "lz4js";

export const decodeArrowBase64 = (base64: string) => {
  // Decode base64 string to Uint8Array
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }

  // Delegate to decodeArrowBytes
  return decodeArrowBytes(bytes);
};

export const decodeArrowBytes = (bytes: ArrayBuffer | Uint8Array) => {
  // Register LZ4 codec before first use
  ensureLZ4CodecRegistered();

  // Use Apache Arrow to parse and decompress the data
  // We do this as `fromArrow` doesn't support compressed
  // codecs, which is _extremely_ space inefficient over
  // the wire
  const arrowTable = tableFromIPC(bytes);

  // Convert to uncompressed Arrow IPC format
  const uncompressedBytes = tableToIPC(arrowTable);

  // Now Arquero can read the uncompressed Arrow data
  let table = fromArrow(uncompressedBytes);

  // Cast columns to appropriate types
  // (Mixed-type columns get converted to strings by Arrow/Pandas)
  table = castColumns(table);

  return table;
};

// Register LZ4 codec (only needs to be done once)
let codecRegistered = false;
function ensureLZ4CodecRegistered(): void {
  if (!codecRegistered) {
    const lz4Codec: Codec = {
      encode(data: Uint8Array): Uint8Array {
        return lz4js.compress(data);
      },
      decode(data: Uint8Array): Uint8Array {
        return lz4js.decompress(data);
      },
    };
    compressionRegistry.set(CompressionType.LZ4_FRAME, lz4Codec);
    codecRegistered = true;
  }
}

// When Arrow/Pandas encounters mixed-type columns (e.g., numbers and nulls),
// it converts everything to strings for safety. This function restores the
// original types based on the value_type column (or a known type).
function castColumns(table: ColumnTable): ColumnTable {
  const columnNames = table.columnNames();
  const hasValue =
    columnNames.includes("value") && columnNames.includes("value_type");
  const hasScanRefusal = columnNames.includes("scan_error_refusal");

  // If neither column needs casting, return as-is
  if (!hasValue && !hasScanRefusal) {
    return table;
  }

  // Helper function to cast a single value based on its type
  const castValue = (
    value: unknown,
    valueType: string
  ): string | number | boolean | null => {
    if (value === null || value === undefined) {
      return null;
    }

    if (valueType === "boolean") {
      // Already boolean
      if (typeof value === "boolean") {
        return value;
      }
      // Cast string to boolean
      const strVal = String(value).toLowerCase();
      if (strVal === "true") {
        return true;
      }
      if (strVal === "false") {
        return false;
      }
      return null;
    } else if (valueType === "number") {
      // Already a number
      if (typeof value === "number") {
        return value;
      }

      const strVal = String(value).trim();
      if (strVal === "") {
        // Empty values should be null
        return null;
      }
      const num = Number(strVal);
      return isNaN(num) ? null : num;
    } else {
      // For string, null, array, object - keep as-is
      return value as string | number | boolean | null;
    }
  };

  // Build derivation object for all columns that need casting
  const derivations: {
    value?: ReturnType<typeof escape>;
    scan_error_refusal?: ReturnType<typeof escape>;
  } = {};

  if (hasValue) {
    derivations.value = escape((d: { value: unknown; value_type: string }) => {
      return castValue(d.value, d.value_type);
    });
  }

  if (hasScanRefusal) {
    derivations.scan_error_refusal = escape(
      (d: { scan_error_refusal: string }) => {
        return d.scan_error_refusal?.toLowerCase() === "true";
      }
    );
  }

  // Apply all derivations in a single pass
  return table.derive(derivations);
}
