import { FC } from "react";

import { SimpleCondition } from "../../query/types";
import { useStore } from "../../state/store";

import styles from "./TranscriptFilterBar.module.css";

export const TranscriptFilterBar: FC = () => {
  const filters = useStore(
    (state) => state.transcriptsTableState.columnFilters
  );
  console.log({ filters });

  return (
    <div className={styles.container}>
      {Object.values(filters).map((f) => {
        return f && <Condition condition={f} />;
      })}
    </div>
  );
};

interface ConditionProps {
  condition: SimpleCondition;
}

const Condition: FC<ConditionProps> = ({ condition }) => {
  return (
    <div>
      {condition.left} {condition.operator} {condition.right}
    </div>
  );
};
