import { FC } from "react";

import { ModelUsage } from "../types/api-types";

import { TokenHeader, TokenRow, TokenTable } from "./TokenTable";

interface ModelTokenTableProps {
  model_usage: ModelUsage;
  className?: string | string[];
}

export const ModelTokenTable: FC<ModelTokenTableProps> = ({
  model_usage,
  className,
}) => {
  return (
    <TokenTable className={className}>
      <TokenHeader />
      <tbody>
        {Object.keys(model_usage).map((key) => {
          if (!model_usage[key]) {
            return null;
          }
          return <TokenRow key={key} model={key} usage={model_usage[key]} />;
        })}
      </tbody>
    </TokenTable>
  );
};
