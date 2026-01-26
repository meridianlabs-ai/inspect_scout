import JSON5 from "json5";

import { basename, dirname } from "./path";

export interface EmbeddedScanState {
  dir: string;
  scan: string;
  scanner?: string;
}

export interface VscodeExtensionInfo {
  /** Protocol version: undefined/1 = legacy V1, 2 = HTTP proxy support */
  protocolVersion?: number;
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
    const state: { type: string; url: string; scanner?: string } = JSON5.parse(
      embeddedState.textContent
    );

    if (state.type === "updateState" && state.url) {
      const url = state.url;
      const dir = dirname(url);
      const scan = basename(url);
      return { dir, scan, scanner: state.scanner };
    }
  } catch (error) {
    console.error("Failed to parse embedded state:", error);
  }

  return null;
}

/**
 * Reads VS Code extension metadata injected into the HTML document.
 * Separate from scan state to cleanly distinguish extension↔frontend protocol info.
 */
export function getVscodeExtensionInfo(): VscodeExtensionInfo | null {
  const element = document.getElementById(
    "vscode-extension-info"
  ) as HTMLScriptElement | null;

  if (!element?.textContent) {
    return null;
  }

  try {
    return JSON5.parse<VscodeExtensionInfo>(element.textContent);
  } catch (error) {
    console.error("Failed to parse vscode-extension-info:", error);
    return null;
  }
}
