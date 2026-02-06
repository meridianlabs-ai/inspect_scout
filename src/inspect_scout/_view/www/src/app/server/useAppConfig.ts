import { useApi } from "../../state/store";
import { AppConfig } from "../../types/api-types";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

/**
 * Loads app config asynchronously at app initialization.
 *
 * Use this hook only at the top of the app before rendering to load config
 * data globally. After this completes, all other components should use
 * useConfig to access the loaded value synchronously.
 */
export const useAppConfigAsync = (): AsyncData<AppConfig> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["config", "project-config-inv"],
    queryFn: () => api.getConfig(),
    staleTime: Infinity,
  });
};

/**
 * Returns app config for use in components after data loaded globally.
 *
 * Use this hook in regular components throughout the app. Assumes the async
 * data has already been loaded at app initialization via useConfigAsync.
 * Throws if data not yet available.
 */
export const useAppConfig = (): AppConfig => {
  const { data } = useAppConfigAsync();
  if (!data) throw new Error("App Config not loaded");
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

/** Strips leading slash from path if present */
function stripLeadingSlash(path: string): string {
  return path.startsWith("/") ? path.slice(1) : path;
}

export function projectOrAppAliasedPath(
  appConfig: AppConfig,
  path: string | null
): string | null {
  if (path == null) {
    return null;
  }

  // Prefer project-relative path when within project directory
  if (appConfig.project_dir && path.startsWith(appConfig.project_dir)) {
    return stripLeadingSlash(path.slice(appConfig.project_dir.length));
  }

  // Fall back to home-aliased path
  return appAliasedPath(appConfig, path);
}
