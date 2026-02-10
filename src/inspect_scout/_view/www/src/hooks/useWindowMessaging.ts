import JSON5 from "json5";
import { useEffect, useMemo } from "react";

import { useAppConfig } from "../app/server/useAppConfig";
import { useLoggingNavigate } from "../debugging/navigationDebugging";
import { scanRoute } from "../router/url";
import { useStore } from "../state/store";
import { basename } from "../utils/path";

export interface UpdateStateMessage {
  type: "updateState";
  url: string;
  scanner?: string;
  extensionProtocolVersion?: number;
}

export interface UpdateRouteMessage {
  type: "updateRoute";
  route: string;
  mode: "full" | "single-file";
  extensionProtocolVersion?: number;
}

export type AppMessage = UpdateStateMessage | UpdateRouteMessage;

function isAppMessage(value: unknown): value is AppMessage {
  return (
    typeof value === "object" &&
    value !== null &&
    "type" in value &&
    (value.type === "updateState" || value.type === "updateRoute")
  );
}

/**
 * Checks for embedded state in the HTML document and parses it.
 * Returns scan directory and name if embedded state exists and is valid.
 */
export function getEmbeddedAppMessage(): AppMessage | null {
  const embeddedState = document.getElementById(
    "scanview-state"
  ) as HTMLScriptElement | null;

  if (!embeddedState?.textContent) {
    return null;
  }

  try {
    const state: unknown = JSON5.parse(embeddedState.textContent);
    if (isAppMessage(state)) {
      return state;
    }
    console.error("Invalid data in the scanview-state element.");
  } catch (error) {
    console.error("Failed to parse embedded state:", error);
  }

  return null;
}

interface MessageContext {
  navigate: ReturnType<typeof useLoggingNavigate>;
  setSingleFileMode: (enabled: boolean) => void;
  setSelectedScanner: (scanner: string) => void;
  scansDir: string;
}

/**
 * Processes an app message by applying store side effects and navigating.
 * Returns true if a navigation was triggered.
 */
function processAppMessage(
  message: AppMessage,
  context: MessageContext,
  options: { skipIfRestoredState: boolean; hasRestoredState: boolean }
): boolean {
  switch (message.type) {
    case "updateRoute": {
      // This is the route used by the most recent version of Inspect Scout. It allows the extension to specify an exact route to navigate to.
      void context.navigate(message.route, { replace: true });
      context.setSingleFileMode(message.mode === "single-file");
      return true;
    }
    case "updateState": {
      // This is a legacy message type. This is only present for legacy support. Drop support anytime after April 2026.
      if (options.skipIfRestoredState && options.hasRestoredState) {
        return false;
      }

      const url = message.url;
      const scan = url ? basename(url) : undefined;
      const scanner = message.scanner;

      if (scanner || scan) {
        context.setSingleFileMode(true);
      }

      if (scanner) {
        context.setSelectedScanner(scanner);
      }

      if (scan) {
        void context.navigate(scanRoute(context.scansDir, scan), {
          replace: true,
        });
        return true;
      }
      return false;
    }
  }
}

export const useWindowMessaging = (): void => {
  const navigate = useLoggingNavigate("useWindowMessaging");
  const setSingleFileMode = useStore((state) => state.setSingleFileMode);
  const setSelectedScanner = useStore((state) => state.setSelectedScanner);
  const selectedScanner = useStore((state) => state.selectedScanner);
  const scansDir = useAppConfig().scans.dir;

  const context: MessageContext = useMemo(() => {
    return {
      navigate,
      setSingleFileMode,
      setSelectedScanner,
      scansDir: scansDir ?? "",
    };
  }, [navigate, setSingleFileMode, setSelectedScanner, scansDir]);

  const hasInitializedEmbeddedData = useStore(
    (state) => state.hasInitializedEmbeddedData
  );
  const setHasInitializedEmbeddedData = useStore(
    (state) => state.setHasInitializedEmbeddedData
  );

  useEffect(() => {
    // When the view is restored after unload, the persisted store already
    // contains the correct state — skip re-processing embedded data.
    if (hasInitializedEmbeddedData) {
      return;
    }
    setHasInitializedEmbeddedData(true);

    // Read and process a message embedded in the document
    const embeddedMessage = getEmbeddedAppMessage();
    if (embeddedMessage) {
      processAppMessage(embeddedMessage, context, {
        skipIfRestoredState: true,
        hasRestoredState: selectedScanner !== undefined,
      });
    }
  }, [
    hasInitializedEmbeddedData,
    setHasInitializedEmbeddedData,
    context,
    selectedScanner,
  ]);

  // Listen for window messages from vscode
  useEffect(() => {
    const onMessage = (e: MessageEvent<unknown>) => {
      if (isAppMessage(e.data)) {
        processAppMessage(e.data, context, {
          skipIfRestoredState: false,
          hasRestoredState: false,
        });
      }
    };

    window.addEventListener("message", onMessage);
    return () => {
      window.removeEventListener("message", onMessage);
    };
  }, [context]);
};
