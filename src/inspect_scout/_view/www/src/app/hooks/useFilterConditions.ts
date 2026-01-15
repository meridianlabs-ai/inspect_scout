import { Condition } from "../../query";
import { SimpleCondition } from "../../query/types";
import { useStore } from "../../state/store";

export const useFilterConditions = () => {
  // The appled filters
  const columnFilters =
    useStore((state) => state.transcriptsTableState.columnFilters) ?? {};

  // Get conditions
  const filterConditions = Object.values(columnFilters)
    .map((filter) => filter.condition)
    .filter((condition): condition is SimpleCondition => Boolean(condition));

  // Reduce to a single condition using 'and'
  const condition = filterConditions.reduce<Condition | undefined>(
    (acc, condition) => (acc ? acc.and(condition) : condition),
    undefined
  );
  return condition;
};
