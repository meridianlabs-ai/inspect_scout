import JSON5 from "json5";

import { basename, dirname } from "./path";

export interface EmbeddedScanState {
  dir: string;
  scan: string;
  scanner?: string;
  /** Protocol version: undefined/1 = legacy V1, 2 = HTTP proxy support */
  extensionProtocolVersion?: number;
}

/**
 * Checks for embedded state in the HTML document and parses it.
 * Returns scan directory and name if embedded state exists and is valid.
 */
export function getEmbeddedScanState(): EmbeddedScanState | null {
  const embeddedState = document.getElementById(
    "scanview-state"
  ) as HTMLScriptElement | null;

  if (!embeddedState || !embeddedState.textContent) {
    return null;
  }

  try {
    const state: {
      type: string;
      url: string;
      scanner?: string;
      extensionProtocolVersion?: number;
    } = JSON5.parse(embeddedState.textContent);

    if (state.type === "updateState" && state.url) {
      const url = decodeURIComponent(state.url);
      const dir = dirname(url);
      const scan = basename(url);
      return {
        dir,
        scan,
        scanner: state.scanner,
        extensionProtocolVersion: state.extensionProtocolVersion,
      };
    }
  } catch (error) {
    console.error("Failed to parse embedded state:", error);
  }

  return null;
}
