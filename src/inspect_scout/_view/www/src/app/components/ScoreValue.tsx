import clsx from "clsx";
import { FC } from "react";

import { MetaDataGrid } from "../../components/content/MetaDataGrid";
import { JsonValue } from "../../types/api-types";
import { isRecord } from "../../utils/type";

interface ScoreProps {
  score: JsonValue;
  className?: string | string[];
  maxRows?: number;
}

export const ScoreValue: FC<ScoreProps> = ({ score, className, maxRows }) => {
  return <div className={clsx(className)}>{renderScore(score, maxRows)}</div>;
};

export const renderScore = (value: JsonValue, maxRows?: number) => {
  if (Array.isArray(value)) {
    return value.join(", ");
  } else if (isRecord(value) && typeof value === "object") {
    return <MetaDataGrid entries={value} maxRows={maxRows} />;
  } else {
    return String(value);
  }
};
