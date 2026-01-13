import { useApi } from "../../state/store";
import { AppConfig } from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";
import { isUri, join } from "../../utils/uri";

/**
 * Loads app config asynchronously at app initialization.
 *
 * Use this hook only at the top of the app before rendering to load config
 * data globally. After this completes, all other components should use
 * useConfig to access the loaded value synchronously.
 */
export const useConfigAsync = (): AsyncData<AppConfig> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["config"],
    queryFn: () => api.getConfig(),
    staleTime: 5000,
    refetchInterval: 5000,
  });
};

/**
 * Returns app config for use in components after data loaded globally.
 *
 * Use this hook in regular components throughout the app. Assumes the async
 * data has already been loaded at app initialization via useConfigAsync.
 * Throws if data not yet available.
 */
export const useConfig = (): AppConfig => {
  const { data } = useConfigAsync();
  if (!data) throw new Error("Config not loaded");
  return data;
};

export function appAliasedPath(
  appConfig: AppConfig,
  path: string | null
): string | null {
  if (path == null) {
    return null;
  }
  return path.replace(appConfig.home_dir, "~");
}

export function appTranscriptsDir(appConfig: AppConfig): string | null {
  const transcripts = appConfig.transcripts || appConfig.project.transcripts;
  if (transcripts) {
    if (isUri(transcripts)) {
      return transcripts;
    } else {
      return join(transcripts, appConfig.project_dir);
    }
  } else {
    return null;
  }
}

export function appScansDir(appConfig: AppConfig): string {
  const scans = appConfig.scans || appConfig.project.scans;
  if (!scans) {
    throw new Error("Scans must be provided in AppConfig.");
  }
  if (isUri(scans)) {
    return scans;
  } else {
    return join(scans, appConfig.project_dir);
  }
}
