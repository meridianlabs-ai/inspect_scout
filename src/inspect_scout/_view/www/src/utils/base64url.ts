/**
 * Encodes a UTF-8 string to base64url format (RFC 4648 Section 5).
 *
 * Base64url is a URL-safe variant of base64 that uses `-` instead of `+`,
 * `_` instead of `/`, and omits padding `=` characters. This makes encoded
 * values safe for use in URLs and filenames without percent-encoding.
 *
 * Used throughout the app to encode directory paths for URL path segments,
 * e.g., `/scans/{dir}` where `{dir}` is a base64url-encoded path like
 * `/Users/alice/scans` -> `L1VzZXJzL2FsaWNlL3NjYW5z`.
 *
 * @param value - The UTF-8 string to encode
 * @returns The base64url-encoded string (no padding)
 *
 * @example
 * encodeBase64Url("/tmp/scans")  // "L3RtcC9zY2Fucw"
 * encodeBase64Url("hello world") // "aGVsbG8gd29ybGQ"
 */
export const encodeBase64Url = (value: string): string => {
  const bytes = new TextEncoder().encode(value);
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });

  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
};

/**
 * Decodes a base64url-encoded string back to UTF-8 (RFC 4648 Section 5).
 *
 * Reverses the base64url encoding by converting URL-safe characters back
 * to standard base64 (`-` -> `+`, `_` -> `/`), restoring padding, and
 * decoding to the original UTF-8 string.
 *
 * Used to decode URL path segments back to filesystem paths, e.g.,
 * extracting the scans directory from `/scans/{dir}` route parameters.
 *
 * @param value - The base64url-encoded string (with or without padding)
 * @returns The decoded UTF-8 string
 * @throws {DOMException} If the input is not valid base64url
 *
 * @example
 * decodeBase64Url("L3RtcC9zY2Fucw")  // "/tmp/scans"
 * decodeBase64Url("aGVsbG8gd29ybGQ") // "hello world"
 */
export const decodeBase64Url = (value: string): string => {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padding = "=".repeat((4 - (normalized.length % 4)) % 4);
  const binary = atob(normalized + padding);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }

  return new TextDecoder().decode(bytes);
};
