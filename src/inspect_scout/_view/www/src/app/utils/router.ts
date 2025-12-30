import { useEffect, useMemo } from "react";
import { useParams } from "react-router-dom";

import { useStore } from "../../state/store";
import { decodeBase64Url } from "../../utils/base64url";

export const useTranscriptDirParams = (): string | undefined => {
  const params = useParams<{ transcriptsDir?: string }>();
  const setUserTranscriptsDir = useStore(
    (state) => state.setUserTranscriptsDir
  );

  const decodedTranscriptDir = useMemo(() => {
    if (params.transcriptsDir) {
      return decodeBase64Url(params.transcriptsDir);
    }
    return undefined;
  }, [params.transcriptsDir]);

  useEffect(() => {
    if (decodedTranscriptDir) {
      setUserTranscriptsDir(decodedTranscriptDir);
    }
  }, [decodedTranscriptDir, setUserTranscriptsDir]);

  return decodedTranscriptDir;
};
