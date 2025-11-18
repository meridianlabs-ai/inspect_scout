import {
  tableFromIPC,
  tableToIPC,
  Codec,
  compressionRegistry,
  CompressionType,
} from "apache-arrow";
import { fromArrow } from "arquero";
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
  const table = fromArrow(uncompressedBytes);
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
