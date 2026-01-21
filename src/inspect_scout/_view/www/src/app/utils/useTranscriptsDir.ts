import { useStore } from "../../state/store";
import { appAliasedPath, useConfig } from "../server/useConfig";

import { useTranscriptDirParams } from "./router";

interface UseTranscriptsDirResult {
  displayTranscriptsDir: string;
  resolvedTranscriptsDir: string;
  setTranscriptsDir: (path: string) => void;
}

export function useTranscriptsDir(
  useRouteParam = false
): UseTranscriptsDirResult {
  const config = useConfig();
  const routeTranscriptsDir = useTranscriptDirParams();
  const userTranscriptsDir = useStore((state) => state.userTranscriptsDir);
  const setUserTranscriptsDir = useStore(
    (state) => state.setUserTranscriptsDir
  );

  // TODO: || "" is a smell. Fix them
  const resolvedPath =
    (useRouteParam ? routeTranscriptsDir : null) ||
    userTranscriptsDir ||
    config.transcripts_dir ||
    "";
  const displayPath = appAliasedPath(config, resolvedPath) || "";

  return {
    displayTranscriptsDir: displayPath,
    resolvedTranscriptsDir: resolvedPath,
    setTranscriptsDir: setUserTranscriptsDir,
  };
}
