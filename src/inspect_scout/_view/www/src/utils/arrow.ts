import { fromArrow } from "arquero";

export const decodeArrowBase64 = (base64: string) => {
  // Decode base64 string to Uint8Array
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }

  // Load Arrow data using Arquero
  const table = fromArrow(bytes.buffer);
  return table;
};

export const decodeArrowBytes = (bytes: ArrayBuffer | Uint8Array) => {
  // Load Arrow data using Arquero
  const table = fromArrow(bytes);
  return table;
};
