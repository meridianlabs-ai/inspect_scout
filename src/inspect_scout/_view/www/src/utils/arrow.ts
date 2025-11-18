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

  // Cast the value column to appropriate types based on value_type
  // (Mixed-type columns get converted to strings by Arrow/Pandas)
  table = castValueColumn(table);

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

/**
 * Cast the 'value' column to its appropriate type based on 'value_type'.
 *
 * When Arrow/Pandas encounters mixed-type columns (e.g., numbers and nulls),
 * it converts everything to strings for safety. This function restores the
 * original types based on the value_type column.
 */
function castValueColumn(table: ColumnTable): ColumnTable {
  // Check if value and value_type columns exist
  if (
    !table.columnNames().includes("value") ||
    !table.columnNames().includes("value_type")
  ) {
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

  // Cast based on each row's value_type
  return table.derive({
    value: escape((d: { value: unknown; value_type: string }) => {
      return castValue(d.value, d.value_type);
    }),
  });
}
