import { useStore } from "../../state/store";
import { appAliasedPath, useAppConfig } from "../server/useAppConfig";

import { useTranscriptDirParams } from "./router";

interface UseTranscriptsDirResult {
  displayTranscriptsDir: string;
  resolvedTranscriptsDir: string;
  resolvedTranscriptsDirSource: "route" | "user" | "project" | "cli";
  setTranscriptsDir: (path: string) => void;
}

export function useTranscriptsDir(
  useRouteParam = false
): UseTranscriptsDirResult {
  const config = useAppConfig();
  const routeTranscriptsDir = useTranscriptDirParams();
  const userTranscriptsDir = useStore((state) => state.userTranscriptsDir);
  const setUserTranscriptsDir = useStore(
    (state) => state.setUserTranscriptsDir
  );

  // TODO: || "" is a smell. Fix them
  const resolvedPath =
    (useRouteParam ? routeTranscriptsDir : null) ||
    userTranscriptsDir ||
    config.transcripts?.dir ||
    "";

  const resolvedSource =
    useRouteParam && routeTranscriptsDir
      ? "route"
      : userTranscriptsDir
        ? "user"
        : config.transcripts && config.transcripts?.source === "cli"
          ? "cli"
          : "project";

  const displayPath = appAliasedPath(config, resolvedPath) || "";

  return {
    displayTranscriptsDir: displayPath,
    resolvedTranscriptsDir: resolvedPath,
    resolvedTranscriptsDirSource: resolvedSource,
    setTranscriptsDir: setUserTranscriptsDir,
  };
}
