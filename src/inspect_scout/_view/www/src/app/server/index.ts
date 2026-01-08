import { SortingState } from "@tanstack/react-table";

import { OrderByModel } from "../../query";

export const sortingStateToOrderBy = (sorting: SortingState): OrderByModel[] =>
  sorting.map((s) => ({ column: s.id, direction: s.desc ? "DESC" : "ASC" }));

export type CursorType = { [key: string]: unknown };
