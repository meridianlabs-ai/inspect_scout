import { skipToken } from "@tanstack/react-query";

import { useAsyncDataFromQuery } from "@tsmono/react/hooks";
import { AsyncData } from "@tsmono/util";

import { Condition } from "../../query/types";
import { useApi } from "../../state/store";

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
