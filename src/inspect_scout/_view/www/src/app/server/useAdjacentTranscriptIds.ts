import { skipToken } from "@tanstack/react-query";
import { SortingState } from "@tanstack/react-table";
import { useEffect, useMemo } from "react";

import { Condition } from "../../query";
import { TranscriptsResponse } from "../../types/api-types";
import { AsyncData, data, loading } from "../../utils/asyncData";

import { useServerTranscriptsInfinite } from "./useServerTranscriptsInfinite";

type Position = { pageIndex: number; itemIndex: number };

/**
 * Returns prev/next transcript IDs relative to the given ID.
 *
 * Note: prev is undefined when viewing the first loaded item.
 * Reverse paging not yet supported - will need backend prev_cursor.
 */
export const useAdjacentTranscriptIds = (
  id: string,
  location?: string | null,
  pageSize?: number,
  filter?: Condition,
  sorting?: SortingState
): AsyncData<[string | undefined, string | undefined]> => {
  const {
    data: queryData,
    error,
    isLoading,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
  } = useServerTranscriptsInfinite(
    location ? { location, pageSize, filter, sorting } : skipToken
  );

  const pages = queryData?.pages;
  const position = useMemo(
    () => (pages ? findPosition(pages, id) : null),
    [pages, id]
  );

  const needsNextPage =
    pages !== undefined &&
    position !== null &&
    isLastLoadedItem(pages, position) &&
    hasNextPage &&
    !isFetchingNextPage;

  useEffect(() => {
    if (needsNextPage) {
      fetchNextPage().catch(console.error);
    }
  }, [needsNextPage, fetchNextPage]);

  if (isLoading) {
    return loading;
  }

  if (error) {
    return { loading: false, error };
  }

  if (pages === undefined || position === null) {
    // ID not found in loaded pages - might need more data
    return loading;
  }

  return data(getAdjacentIds(pages, position));
};

const findPosition = (
  pages: TranscriptsResponse[],
  id: string
): Position | null => {
  for (let p = 0; p < pages.length; p++) {
    const page = pages[p];
    if (!page) continue;
    const i = page.items.findIndex((item) => item.transcript_id === id);
    if (i >= 0) return { pageIndex: p, itemIndex: i };
  }
  return null;
};

const getAdjacentIds = (
  pages: TranscriptsResponse[],
  pos: Position
): [string | undefined, string | undefined] => {
  const page = pages[pos.pageIndex]!;
  // Note: prevId is undefined at position 0; reverse paging not yet supported
  const prevId =
    pos.itemIndex > 0
      ? page.items[pos.itemIndex - 1]?.transcript_id
      : pages[pos.pageIndex - 1]?.items.at(-1)?.transcript_id;
  const nextId =
    pos.itemIndex < page.items.length - 1
      ? page.items[pos.itemIndex + 1]?.transcript_id
      : pages[pos.pageIndex + 1]?.items[0]?.transcript_id;
  return [prevId, nextId];
};

const isLastLoadedItem = (
  pages: TranscriptsResponse[],
  pos: Position
): boolean =>
  pos.pageIndex === pages.length - 1 &&
  pos.itemIndex === pages[pos.pageIndex]!.items.length - 1;
