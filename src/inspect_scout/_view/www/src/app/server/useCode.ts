import { Condition } from "../../query/types";
import { useApi } from "../../state/store";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

export const useCode = (
  condition: Condition
): AsyncData<Record<string, string>> => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: ["code", condition],
    queryFn: () => api.postCode(condition),
    staleTime: Infinity,
  });
};
