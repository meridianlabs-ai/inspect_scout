/**
 * Default sizing strategy - uses the column's defined `size` property.
 */

import { ColumnSizingState } from "@tanstack/react-table";

import { SizingStrategy } from "./types";
import { getColumnId } from "./utils";

export const defaultStrategy: SizingStrategy = {
  computeSizes({ columns }): ColumnSizingState {
    const sizing: ColumnSizingState = {};

    for (const column of columns) {
      const id = getColumnId(column);
      if (id && column.size !== undefined) {
        sizing[id] = column.size;
      }
    }

    return sizing;
  },
};
