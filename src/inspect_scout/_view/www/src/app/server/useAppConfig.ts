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
    queryKey: ["config", "serverConfig"],
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
