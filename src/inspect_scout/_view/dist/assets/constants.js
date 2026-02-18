import { s as sortingStateToOrderBy, u as useInfiniteQuery } from "./index2.js";
import { u as useApi, r as reactExports, y as skipToken, bN as keepPreviousData } from "./index.js";
const useServerTranscriptsInfinite = (params) => {
  const api = useApi();
  const orderBy = reactExports.useMemo(
    () => params !== skipToken && params.sorting ? sortingStateToOrderBy(params.sorting) : void 0,
    [params]
  );
  const pageSize = params !== skipToken ? params.pageSize ?? 50 : 50;
  return useInfiniteQuery({
    queryKey: params === skipToken ? [skipToken] : [
      "transcripts-infinite",
      params.location,
      params.filter,
      orderBy,
      pageSize,
      "project-config-inv"
    ],
    queryFn: params === skipToken ? skipToken : async ({ pageParam }) => {
      const pagination = pageParam ? {
        limit: pageSize,
        cursor: pageParam,
        direction: "forward"
      } : {
        limit: pageSize,
        cursor: null,
        direction: "forward"
      };
      return await api.getTranscripts(
        params.location,
        params.filter,
        orderBy,
        pagination
      );
    },
    initialPageParam: void 0,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? void 0,
    staleTime: 10 * 60 * 1e3,
    refetchInterval: 10 * 60 * 1e3,
    placeholderData: keepPreviousData
  });
};
const TRANSCRIPTS_INFINITE_SCROLL_CONFIG = {
  /** Number of rows to fetch per page (500 rows = 14,500px at 29px/row) */
  pageSize: 500,
  /** Distance from bottom (in px) at which to trigger fetch (~69 rows) */
  threshold: 2e3
};
export {
  TRANSCRIPTS_INFINITE_SCROLL_CONFIG as T,
  useServerTranscriptsInfinite as u
};
//# sourceMappingURL=constants.js.map
