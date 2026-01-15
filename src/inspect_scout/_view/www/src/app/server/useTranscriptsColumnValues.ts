import { ScalarValue } from "../../api/api";
import { Condition } from "../../query";
import { useApi } from "../../state/store";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

export const useTranscriptsColumnValues = (
  location: string | undefined,
  column: string | undefined,
  filter: Condition | undefined
): AsyncData<ScalarValue[]> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["transcriptsColumnValues", location, column, filter],
    queryFn: () =>
      api.getTranscriptsColumnValues(location ?? "", column ?? "", filter),
    staleTime: 10 * 60 * 1000, // We can be pretty liberal here
    enabled: !!location && !!column,
  });
};
