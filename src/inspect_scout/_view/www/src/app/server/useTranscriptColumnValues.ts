import { ScalarValue } from "../../api/api";
import { Condition } from "../../query";
import { useApi } from "../../state/store";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

export const useTranscriptColumnValues = (
  transcriptsDir: string,
  column: string,
  filter?: Condition
): AsyncData<ScalarValue[]> => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: ["transcriptColumnValues", transcriptsDir, column, filter],
    queryFn: () =>
      api.getTranscriptColumnValues(transcriptsDir, column, filter),
    staleTime: 10 * 60 * 1000, // We can be pretty liberal here
  });
};
