import { Condition } from "../../query/types";
import { useApi } from "../../state/store";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

export const useCode = (
  condition: Condition | undefined
): AsyncData<Record<string, string>> => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: ["code", condition],
    enabled: !!condition,
    queryFn: () => api.postCode(condition!),
    staleTime: Infinity,
  });
};
