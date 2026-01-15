import { skipToken } from "@tanstack/react-query";

import { Condition } from "../../query/types";
import { useApi } from "../../state/store";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

export const useCode = (
  condition: Condition | typeof skipToken
): AsyncData<Record<string, string>> => {
  const api = useApi();
  return useAsyncDataFromQuery({
    queryKey: ["code", condition],
    queryFn:
      condition === skipToken ? skipToken : () => api.postCode(condition),
    staleTime: Infinity,
  });
};
