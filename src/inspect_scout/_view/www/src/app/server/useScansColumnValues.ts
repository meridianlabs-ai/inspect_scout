import { skipToken } from "@tanstack/react-query";

import { ScalarValue } from "../../api/api";
import { Condition } from "../../query";
import { useApi } from "../../state/store";
import { AsyncData } from "../../utils/asyncData";
import { useAsyncDataFromQuery } from "../../utils/asyncDataFromQuery";

type ScansColumnValuesParams = {
  location: string;
  column: string;
  filter: Condition | undefined;
};

export const useScansColumnValues = (
  params: ScansColumnValuesParams | typeof skipToken
): AsyncData<ScalarValue[]> => {
  const api = useApi();

  return useAsyncDataFromQuery({
    queryKey: ["scansColumnValues", params],
    queryFn:
      params === skipToken
        ? skipToken
        : () =>
            api.getScansColumnValues(
              params.location,
              params.column,
              params.filter
            ),
    staleTime: 10 * 60 * 1000, // We can be pretty liberal here
  });
};
