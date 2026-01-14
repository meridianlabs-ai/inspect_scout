import { ScalarValue } from "../../api/api";
import { Condition } from "../../query";
import { useApi } from "../../state/store";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

export const useTranscriptsColumnValues = (
  transcriptsDir: string,
  column: string,
  filter: Condition | undefined
): AsyncData<ScalarValue[]> => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: ["transcriptsColumnValues", transcriptsDir, column, filter],
    queryFn: () =>
      api.getTranscriptsColumnValues(transcriptsDir, column, filter),
    staleTime: 10 * 60 * 1000, // We can be pretty liberal here
  });
};
