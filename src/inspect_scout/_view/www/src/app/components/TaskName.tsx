import clsx from "clsx";
import { FC, ReactNode } from "react";

interface TaskNameProps {
  taskSet?: string;
  taskId?: string | number;
  taskRepeat?: number;
}

export const TaskName: FC<TaskNameProps> = ({
  taskSet,
  taskId,
  taskRepeat,
}) => {
  if (!taskSet && !taskId && taskRepeat === undefined) {
    return "<unknown>";
  }

  const results: ReactNode[] = [
    <span key={"task-column-task-set"}>{taskSet || "<unknown>"}</span>,
  ];

  if (taskId) {
    results.push("/", <span key={"task-column-task-id"}>{taskId}</span>);
  }
  if (taskRepeat !== undefined) {
    results.push(
      " ",
      <span
        key={"task-column-task-repeat"}
        className={clsx("text-style-secondary", "text-size-smallest")}
      >{`(${taskRepeat})`}</span>
    );
  }

  return results;
};
