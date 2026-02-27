import { M as useParams, u as useStore, r as reactExports, a3 as decodeBase64Url, e as useAppConfig, Y as appAliasedPath } from "./index.js";
const useTranscriptDirParams = () => {
  const params = useParams();
  const setUserTranscriptsDir = useStore(
    (state) => state.setUserTranscriptsDir
  );
  const decodedTranscriptDir = reactExports.useMemo(() => {
    if (params.transcriptsDir) {
      return decodeBase64Url(params.transcriptsDir);
    }
    return void 0;
  }, [params.transcriptsDir]);
  reactExports.useEffect(() => {
    if (decodedTranscriptDir) {
      setUserTranscriptsDir(decodedTranscriptDir);
    }
  }, [decodedTranscriptDir, setUserTranscriptsDir]);
  return decodedTranscriptDir;
};
function useTranscriptsDir(useRouteParam = false) {
  const config = useAppConfig();
  const routeTranscriptsDir = useTranscriptDirParams();
  const userTranscriptsDir = useStore((state) => state.userTranscriptsDir);
  const setUserTranscriptsDir = useStore(
    (state) => state.setUserTranscriptsDir
  );
  const resolvedPath = (useRouteParam ? routeTranscriptsDir : null) || userTranscriptsDir || config.transcripts?.dir || "";
  const resolvedSource = useRouteParam && routeTranscriptsDir ? "route" : userTranscriptsDir ? "user" : config.transcripts && config.transcripts?.source === "cli" ? "cli" : "project";
  const displayPath = appAliasedPath(config, resolvedPath) || "";
  return {
    displayTranscriptsDir: displayPath,
    resolvedTranscriptsDir: resolvedPath,
    resolvedTranscriptsDirSource: resolvedSource,
    setTranscriptsDir: setUserTranscriptsDir
  };
}
export {
  useTranscriptsDir as u
};
//# sourceMappingURL=useTranscriptsDir.js.map
