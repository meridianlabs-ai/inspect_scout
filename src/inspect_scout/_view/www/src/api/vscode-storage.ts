/**
 * VS Code storage adapter for ClientStorage interface.
 */

import { VSCodeApi } from "../utils/vscode";

import { ClientStorage } from "./api";

export const createVSCodeStore = (api: VSCodeApi): ClientStorage => ({
  getItem: (key: string): string | null => {
    const state = api.getState();
    if (state && typeof state === "object") {
      const stateObj = state as Record<string, string>;
      return stateObj[key] || null;
    }
    return null;
  },
  setItem: (key: string, value: string): void => {
    const existingState = api.getState() || {};
    const stateObj = (
      typeof existingState === "object" ? existingState : {}
    ) as Record<string, string>;
    stateObj[key] = value;
    api.setState(stateObj);
  },
  removeItem: (key: string): void => {
    const existingState = api.getState();
    if (existingState && typeof existingState === "object") {
      const stateObj = existingState as Record<string, string>;
      delete stateObj[key];
      api.setState(stateObj);
    }
  },
});
